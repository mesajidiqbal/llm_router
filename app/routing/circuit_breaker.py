import time
from app.storage.memory import MemoryStore


class CircuitBreaker:
    FAILURE_THRESHOLD = 3
    OPEN_DURATION_SECONDS = 60

    def __init__(self):
        self.memory = MemoryStore()

    async def is_available(self, provider_name: str) -> bool:
        state = await self.memory.get_provider_dynamic_state(provider_name)
        consecutive_failures = state["consecutive_failures"]
        open_until_ts = state["open_until_ts"]
        
        if consecutive_failures < self.FAILURE_THRESHOLD:
            return True
        
        now = time.time()
        
        if open_until_ts > 0 and now < open_until_ts:
            return False
        
        if open_until_ts > 0 and now >= open_until_ts:
            if not state["half_open_probe_in_flight"]:
                await self.memory.set_half_open_probe(provider_name, True)
                return True
            else:
                return False
        
        return True

    async def record_outcome(self, provider_name: str, success: bool):
        state = await self.memory.get_provider_dynamic_state(provider_name)
        
        if success:
            await self.memory.record_success(provider_name)
            await self.memory.clear_circuit_open(provider_name)
            await self.memory.set_half_open_probe(provider_name, False)
        else:
            await self.memory.record_failure(provider_name)
            
            state = await self.memory.get_provider_dynamic_state(provider_name)
            consecutive_failures = state["consecutive_failures"]
            
            if consecutive_failures >= self.FAILURE_THRESHOLD:
                open_until = time.time() + self.OPEN_DURATION_SECONDS
                await self.memory.set_circuit_open(provider_name, open_until)
            
            await self.memory.set_half_open_probe(provider_name, False)

    async def get_status(self, provider_name: str) -> str:
        state = await self.memory.get_provider_dynamic_state(provider_name)
        consecutive_failures = state["consecutive_failures"]
        open_until_ts = state["open_until_ts"]

        
        if consecutive_failures < self.FAILURE_THRESHOLD:
            return "CLOSED"
        
        now = time.time()
        
        if open_until_ts > 0 and now < open_until_ts:
            return "OPEN"
        
        if open_until_ts > 0 and now >= open_until_ts:
            return "HALF_OPEN"
        
        return "CLOSED"
