from shared_memory.memory_manager import SharedMemory


memory = SharedMemory()

memory.set("project_status", "running")

print(memory.get("project_status"))