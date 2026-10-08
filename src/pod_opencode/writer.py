def write_project(project, output_path: str):
    """Write a project to MSPDI XML format. ProjectLibre can open MSPDI XML files."""
    if output_path.endswith(".pod"):
        raise ValueError(
            "Output must be .xml (MPXJ cannot write POD format). "
            "ProjectLibre can open .xml files directly."
        )

    try:
        from org.mpxj.mspdi import MSPDIWriter
        writer = MSPDIWriter()
        writer.write(project, output_path)
    except ImportError as e:
        raise RuntimeError(f"Failed to import MSPDIWriter: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to write project to '{output_path}': {e}") from e
