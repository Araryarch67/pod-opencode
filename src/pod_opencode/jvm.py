import atexit

_jvm_started = False


def start_jvm():
    """Start the JPype JVM if not already running. Idempotent — safe to call multiple times."""
    global _jvm_started
    if _jvm_started:
        return

    try:
        import jpype

        if not jpype.isJVMStarted():
            import mpxj
            jpype.startJVM()
        _jvm_started = True
    except Exception as e:
        raise RuntimeError(f"Failed to start JVM: {e}") from e


def shutdown_jvm():
    """Shut down the JPype JVM if it is running."""
    try:
        import jpype
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
    except Exception:
        pass  # Ignore errors during shutdown
