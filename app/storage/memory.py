import asyncio
import time
from typing import Optional


from app.providers.base import RateLimitError





class MemoryStore:
    _instance: Optional['MemoryStore'] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._provider_lock = asyncio.Lock()
        
        self._is_down: dict[str, bool] = {}
        self._consecutive_failures: dict[str, int] = {}
        self._open_until_ts: dict[str, float] = {}
        self._half_open_probe: dict[str, bool] = {}
        
        self._rate_window_start: dict[str, float] = {}
        self._rate_window_count: dict[str, int] = {}
        
        self._total_requests = 0
        self._total_success = 0
        self._total_failures = 0
        self._total_latency_sum = 0.0
        self._total_cost = 0.0
        
        self._provider_requests: dict[str, int] = {}
        self._provider_success: dict[str, int] = {}
        self._provider_failures: dict[str, int] = {}
        self._provider_latency_sum: dict[str, float] = {}
        
        self._user_spend: dict[str, float] = {}
        
        self._initialized = True

    async def get_provider_dynamic_state(self, name: str) -> dict:
        async with self._provider_lock:
            return {
                "is_down": self._is_down.get(name, False),
                "consecutive_failures": self._consecutive_failures.get(name, 0),
                "open_until_ts": self._open_until_ts.get(name, 0),
                "half_open_probe_in_flight": self._half_open_probe.get(name, False),
            }

    async def set_provider_down(self, name: str, down: bool):
        async with self._provider_lock:
            self._is_down[name] = down

    async def record_failure(self, name: str):
        async with self._provider_lock:
            self._consecutive_failures[name] = self._consecutive_failures.get(name, 0) + 1

    async def record_success(self, name: str):
        async with self._provider_lock:
            self._consecutive_failures[name] = 0

    async def get_user_spend(self, user_id: str) -> float:
        async with self._provider_lock:
            return self._user_spend.get(user_id, 0.0)

    async def add_user_spend(self, user_id: str, cost: float):
        async with self._provider_lock:
            self._user_spend[user_id] = self._user_spend.get(user_id, 0.0) + cost

    async def record_request_metrics(self, provider_name: str, latency_ms: int, cost: float, success: bool):
        async with self._provider_lock:
            self._total_requests += 1
            
            if provider_name not in self._provider_requests:
                self._provider_requests[provider_name] = 0
                self._provider_success[provider_name] = 0
                self._provider_failures[provider_name] = 0
                self._provider_latency_sum[provider_name] = 0.0
            
            self._provider_requests[provider_name] += 1
            
            if success:
                self._total_success += 1
                self._provider_success[provider_name] += 1
                self._total_latency_sum += latency_ms
                self._provider_latency_sum[provider_name] += latency_ms
                self._total_cost += cost
            else:
                self._total_failures += 1
                self._provider_failures[provider_name] += 1

    async def check_and_increment_rate_limit(self, provider_name: str, rpm_limit: int):
        async with self._provider_lock:
            now = time.time()
            
            window_start = self._rate_window_start.get(provider_name, now)
            window_count = self._rate_window_count.get(provider_name, 0)
            
            if now - window_start >= 60:
                self._rate_window_start[provider_name] = now
                self._rate_window_count[provider_name] = 0
                window_count = 0
            
            self._rate_window_count[provider_name] = window_count + 1
            
            if self._rate_window_count[provider_name] > rpm_limit:
                raise RateLimitError(f"Rate limit exceeded for {provider_name}")

    async def get_global_metrics(self) -> dict:
        async with self._provider_lock:
            success_rate = self._total_success / self._total_requests if self._total_requests > 0 else 1.0
            avg_latency = self._total_latency_sum / self._total_success if self._total_success > 0 else 0.0
            
            return {
                "total_requests": self._total_requests,
                "total_success": self._total_success,
                "total_failures": self._total_failures,
                "avg_latency_ms": avg_latency,
                "total_cost": self._total_cost,
                "success_rate": success_rate,
            }

    async def get_provider_metrics(self) -> dict[str, dict]:
        async with self._provider_lock:
            metrics = {}
            for provider_name in self._provider_requests.keys():
                requests = self._provider_requests[provider_name]
                successes = self._provider_success[provider_name]
                failures = self._provider_failures[provider_name]
                latency_sum = self._provider_latency_sum[provider_name]
                
                success_rate = successes / requests if requests > 0 else 1.0
                avg_latency = latency_sum / successes if successes > 0 else 0.0
                
                metrics[provider_name] = {
                    "requests": requests,
                    "success": successes,
                    "failures": failures,
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency,
                }
            
            return metrics

    async def set_circuit_open(self, name: str, open_until_ts: float):
        async with self._provider_lock:
            self._open_until_ts[name] = open_until_ts

    async def clear_circuit_open(self, name: str):
        async with self._provider_lock:
            self._open_until_ts[name] = 0

    async def set_half_open_probe(self, name: str, in_flight: bool):
        async with self._provider_lock:
            self._half_open_probe[name] = in_flight
