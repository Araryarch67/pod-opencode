POD_SEPARATOR = b"@@@@@@@@@@ProjectLibreSeparator_MSXML@@@@@@@@@@"
POD_JAVA_MAGIC = bytes((0xAC, 0xED, 0x00, 0x05))
POD_PLACEHOLDER_SIZE = 600


def apply_project_name(project, project_name):
    """Set the project name (shown as window title in ProjectLibre).

    Sets both Name and Title properties so the new name is picked up
    no matter which one the importing application displays.
    A None name leaves the project unchanged.
    """
    if project_name is None:
        return
    props = project.getProjectProperties()
    props.setName(project_name)
    props.setProjectTitle(project_name)


def write_project(project, output_path: str):
    """Write a project to MSPDI XML format. ProjectLibre can open MSPDI XML files."""
    try:
        from org.mpxj.mspdi import MSPDIWriter

        writer = MSPDIWriter()
        writer.write(project, output_path)
    except ImportError as e:
        raise RuntimeError(f"Failed to import MSPDIWriter: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to write project to '{output_path}': {e}") from e


def write_pod(project, output_path: str):
    """Write a project to ProjectLibre .pod format.

    A .pod file is a Java-serialization header, the ProjectLibre separator,
    and an embedded MSPDI document. ProjectLibre reads the MSPDI part
    (via its built-in XML recovery path); MPXJ reads it via
    ProjectLibreReader. The placeholder header carries no schedule data.

    NOTE: opening the produced file in ProjectLibre GUI still needs a
    one-time manual confirmation.
    """
    try:
        import jpype
        from org.mpxj.mspdi import MSPDIWriter

        buffer = jpype.java.io.ByteArrayOutputStream()
        MSPDIWriter().write(project, buffer)
        mspdi_bytes = bytes(buffer.toByteArray())

        padding = (b"POD-OPENCODE-PLACEHOLDER-v1 " * 30)[:POD_PLACEHOLDER_SIZE]
        header = (POD_JAVA_MAGIC + padding).ljust(POD_PLACEHOLDER_SIZE, b"\x00")
        with open(output_path, "wb") as f:
            f.write(header + POD_SEPARATOR + mspdi_bytes)
    except ImportError as e:
        raise RuntimeError(f"Failed to import MSPDIWriter: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to write POD file to '{output_path}': {e}") from e


def write_output(project, output_path: str):
    """Write to .xml (MSPDI) or .pod depending on the output extension."""
    if output_path.lower().endswith(".pod"):
        write_pod(project, output_path)
    else:
        write_project(project, output_path)
