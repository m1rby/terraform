# backend/plugin_manager.py
"""
Менеджер плагинов для подключения внешних обработчиков через gRPC
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

# Опциональный импорт gRPC
try:
    import grpc
    GRPC_AVAILABLE = True
except ImportError:
    grpc = None
    GRPC_AVAILABLE = False
    print("⚠ gRPC не установлен. Плагинная система недоступна.")
    print("  Установите: pip install grpcio grpcio-tools protobuf")

# После генерации proto файлов:
# python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/plugin.proto
try:
    import plugin_pb2
    import plugin_pb2_grpc
except ImportError:
    # Заглушка если proto еще не сгенерированы
    plugin_pb2 = None
    plugin_pb2_grpc = None


@dataclass
class PluginConfig:
    """Конфигурация плагина"""
    name: str
    address: str  # host:port для gRPC
    enabled: bool = True
    timeout: int = 5  # секунды
    capabilities: List[str] = None


class PluginManager:
    """Менеджер для работы с плагинами"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginConfig] = {}
        self.channels: Dict[str, grpc.Channel] = {}
        self.stubs: Dict[str, Any] = {}
    
    def register_plugin(self, config: PluginConfig):
        """Регистрация нового плагина"""
        self.plugins[config.name] = config
        
        if config.enabled:
            try:
                # Создаем gRPC канал
                channel = grpc.insecure_channel(config.address)
                self.channels[config.name] = channel
                
                if plugin_pb2_grpc:
                    stub = plugin_pb2_grpc.LogPluginStub(channel)
                    self.stubs[config.name] = stub
                    
                    # Получаем информацию о плагине
                    info = self._get_plugin_info(config.name)
                    if info:
                        config.capabilities = info.get('capabilities', [])
                        print(f"✓ Плагин '{config.name}' подключен: {info.get('description', '')}")
                else:
                    print(f"⚠ Proto файлы не сгенерированы, плагин '{config.name}' в режиме заглушки")
            except Exception as e:
                print(f"✗ Ошибка подключения плагина '{config.name}': {e}")
    
    def _get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """Получение информации о плагине"""
        if plugin_name not in self.stubs or not plugin_pb2:
            return None
        
        try:
            stub = self.stubs[plugin_name]
            request = plugin_pb2.PluginInfoRequest()
            response = stub.GetPluginInfo(request, timeout=self.plugins[plugin_name].timeout)
            
            return {
                'name': response.name,
                'version': response.version,
                'description': response.description,
                'capabilities': list(response.capabilities)
            }
        except Exception as e:
            print(f"Ошибка получения информации о плагине '{plugin_name}': {e}")
            return None
    
    def filter_logs(self, logs: List[Dict], plugin_name: str, filter_params: Dict = None) -> List[Dict]:
        """Фильтрация логов через плагин"""
        if plugin_name not in self.stubs or not plugin_pb2:
            return logs
        
        try:
            stub = self.stubs[plugin_name]
            
            # Конвертируем логи в proto формат
            proto_logs = [self._dict_to_log_entry(log) for log in logs]
            
            request = plugin_pb2.FilterRequest(
                logs=proto_logs,
                filter_params=filter_params or {}
            )
            
            response = stub.FilterLogs(request, timeout=self.plugins[plugin_name].timeout)
            
            # Конвертируем обратно в dict
            return [self._log_entry_to_dict(log) for log in response.filtered_logs]
        except Exception as e:
            print(f"Ошибка фильтрации через плагин '{plugin_name}': {e}")
            return logs
    
    def process_logs(self, logs: List[Dict], plugin_name: str, process_params: Dict = None) -> tuple[List[Dict], Dict]:
        """Обработка логов через плагин"""
        if plugin_name not in self.stubs or not plugin_pb2:
            return logs, {}
        
        try:
            stub = self.stubs[plugin_name]
            
            proto_logs = [self._dict_to_log_entry(log) for log in logs]
            
            request = plugin_pb2.ProcessRequest(
                logs=proto_logs,
                process_params=process_params or {}
            )
            
            response = stub.ProcessLogs(request, timeout=self.plugins[plugin_name].timeout)
            
            processed = [self._log_entry_to_dict(log) for log in response.processed_logs]
            metadata = dict(response.metadata)
            
            return processed, metadata
        except Exception as e:
            print(f"Ошибка обработки через плагин '{plugin_name}': {e}")
            return logs, {}
    
    def aggregate_logs(self, logs: List[Dict], plugin_name: str, agg_type: str = "error_grouping", 
                      agg_params: Dict = None) -> List[Dict]:
        """Агрегация логов через плагин"""
        if plugin_name not in self.stubs or not plugin_pb2:
            return []
        
        try:
            stub = self.stubs[plugin_name]
            
            proto_logs = [self._dict_to_log_entry(log) for log in logs]
            
            request = plugin_pb2.AggregateRequest(
                logs=proto_logs,
                aggregation_type=agg_type,
                agg_params=agg_params or {}
            )
            
            response = stub.AggregateLogs(request, timeout=self.plugins[plugin_name].timeout)
            
            # Конвертируем результаты агрегации
            results = []
            for result in response.results:
                results.append({
                    'group_key': result.group_key,
                    'count': result.count,
                    'sample_logs': [self._log_entry_to_dict(log) for log in result.sample_logs],
                    'metadata': dict(result.metadata)
                })
            
            return results
        except Exception as e:
            print(f"Ошибка агрегации через плагин '{plugin_name}': {e}")
            return []
    
    def _dict_to_log_entry(self, log_dict: Dict) -> Any:
        """Конвертация dict в LogEntry proto"""
        if not plugin_pb2:
            return None
        
        return plugin_pb2.LogEntry(
            timestamp=log_dict.get('timestamp', ''),
            level=log_dict.get('level', ''),
            message=log_dict.get('message', ''),
            raw=log_dict.get('raw', ''),
            tf_req_id=log_dict.get('tf_req_id', ''),
            tf_section=log_dict.get('tf_section', ''),
            tf_rpc=log_dict.get('tf_rpc', ''),
            source_filename=log_dict.get('source_filename', ''),
            invalid=log_dict.get('invalid', False),
            extra_fields={k: str(v) for k, v in log_dict.items() 
                         if k not in ['timestamp', 'level', 'message', 'raw', 'tf_req_id', 
                                     'tf_section', 'tf_rpc', 'source_filename', 'invalid']}
        )
    
    def _log_entry_to_dict(self, log_entry: Any) -> Dict:
        """Конвертация LogEntry proto в dict"""
        result = {
            'timestamp': log_entry.timestamp,
            'level': log_entry.level,
            'message': log_entry.message,
            'raw': log_entry.raw,
            'tf_req_id': log_entry.tf_req_id,
            'tf_section': log_entry.tf_section,
            'tf_rpc': log_entry.tf_rpc,
            'source_filename': log_entry.source_filename,
            'invalid': log_entry.invalid,
        }
        
        # Добавляем extra поля
        result.update(dict(log_entry.extra_fields))
        
        return result
    
    def list_plugins(self) -> List[Dict]:
        """Список всех зарегистрированных плагинов"""
        return [
            {
                'name': name,
                'address': config.address,
                'enabled': config.enabled,
                'capabilities': config.capabilities or []
            }
            for name, config in self.plugins.items()
        ]
    
    def shutdown(self):
        """Закрытие всех соединений"""
        for channel in self.channels.values():
            channel.close()


# Глобальный экземпляр менеджера
plugin_manager = PluginManager()
