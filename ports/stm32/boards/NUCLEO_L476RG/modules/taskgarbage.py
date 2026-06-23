from gc import collect, disable


# Run garbage collection cooperatively with other tasks.
def run():
    disable()
    while True:
        collect()
        yield None
