from task_base import Task_Base
from gc import collect, enable, disable

class Task_Garbage(Task_Base):
    
    def __init__(self):
        # Initialize the parent class
        super().__init__()

    def run(self):
        disable()
        while True:
            collect()
            yield None