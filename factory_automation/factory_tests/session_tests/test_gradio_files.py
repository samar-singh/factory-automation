#!/usr/bin/env python3
"""Test what Gradio file upload returns"""

import gradio as gr
import json


def test_file_upload(files):
    """Test what Gradio returns for uploaded files"""

    result = {
        "files_type": str(type(files)),
        "files_value": str(files) if files else None,
        "file_details": [],
    }

    if files:
        for i, file_item in enumerate(files):
            file_info = {
                "index": i,
                "type": str(type(file_item)),
                "value": str(file_item),
                "is_string": isinstance(file_item, str),
                "is_dict": isinstance(file_item, dict),
                "is_tuple": isinstance(file_item, tuple),
            }

            # If it's a string, it's likely a file path
            if isinstance(file_item, str):
                import os

                file_info["exists"] = os.path.exists(file_item)
                file_info["absolute_path"] = (
                    os.path.abspath(file_item) if os.path.exists(file_item) else None
                )

            result["file_details"].append(file_info)

    return json.dumps(result, indent=2)


# Create simple test interface
with gr.Blocks() as app:
    gr.Markdown("# Test Gradio File Upload")

    files = gr.File(
        label="Upload Files",
        file_count="multiple",
        type="filepath",  # This should return file paths
    )

    output = gr.JSON(label="File Upload Result")

    test_btn = gr.Button("Test Files")

    test_btn.click(fn=test_file_upload, inputs=[files], outputs=[output])

if __name__ == "__main__":
    app.launch(server_port=7861)
