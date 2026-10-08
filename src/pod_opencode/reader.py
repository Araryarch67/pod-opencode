def read_project(path: str):
    """Read a project file (POD or MSPDI XML) and return a Java ProjectFile object."""
    try:
        from org.mpxj.reader import UniversalProjectReader
        reader = UniversalProjectReader()
        project = reader.read(path)
        return project
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to read project file '{path}': {e}") from e
