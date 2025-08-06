"""Trace Dashboard for monitoring agent actions in Gradio"""

from typing import List

import gradio as gr

from ..factory_utils.trace_monitor import trace_monitor


def get_trace_list() -> List[List[str]]:
    """Get list of traces for display"""
    traces = []
    for trace in trace_monitor.traces:
        traces.append(
            [
                trace["trace_name"],
                trace["status"],
                f"{trace.get('duration_seconds', 0):.2f}s",
                str(len(trace.get("tool_calls", []))),
                trace["start_time"],
            ]
        )
    return traces[-20:]  # Last 20 traces


def get_trace_details(trace_name: str) -> str:
    """Get detailed view of a specific trace"""
    if not trace_name:
        return "Select a trace to view details"

    return trace_monitor.visualize_trace(trace_name)


def get_tool_analytics() -> str:
    """Get tool usage analytics"""
    analytics = trace_monitor.get_tool_analytics()

    output = ["📊 TOOL USAGE ANALYTICS\n"]
    output.append(f"Total Tool Calls: {analytics['total_tool_calls']}")
    output.append(f"Unique Tools Used: {analytics['unique_tools']}")
    output.append(
        f"Average Tools per Trace: {analytics['average_tools_per_trace']:.2f}"
    )

    if analytics["most_used_tool"]:
        output.append(
            f"\nMost Used Tool: {analytics['most_used_tool'][0]} ({analytics['most_used_tool'][1]} calls)"
        )

    output.append("\n🔧 Tool Frequency:")
    for tool, count in analytics["tool_frequency"].items():
        output.append(f"  - {tool}: {count}")

    if analytics["common_tool_sequences"]:
        output.append("\n🔄 Common Tool Sequences:")
        for seq, count in analytics["common_tool_sequences"].items():
            output.append(f"  - {seq}: {count} times")

    return "\n".join(output)


def get_current_trace_status() -> str:
    """Get status of current running trace"""
    if trace_monitor.current_trace:
        trace = trace_monitor.current_trace
        output = [f"🏃 CURRENTLY RUNNING: {trace['trace_name']}"]
        output.append(f"Started: {trace['start_time']}")
        output.append(f"Tools Called: {len(trace['tool_calls'])}")

        if trace["tool_calls"]:
            output.append("\nRecent Tools:")
            for tool in trace["tool_calls"][-3:]:
                output.append(f"  - {tool['tool']}")

        return "\n".join(output)
    else:
        return "No trace currently running"


def export_traces() -> str:
    """Export all traces to file"""
    filename = trace_monitor.export_traces()
    return f"✅ Traces exported to: {filename}"


def create_trace_dashboard() -> gr.Blocks:
    """Create Gradio dashboard for trace monitoring"""

    with gr.Blocks(title="Agent Trace Monitor") as dashboard:
        gr.Markdown("# 🔍 Agent Trace Monitor")
        gr.Markdown("Monitor autonomous agent actions and tool usage in real-time")

        with gr.Tab("Live Monitoring"):
            with gr.Row():
                with gr.Column(scale=1):
                    current_status = gr.Textbox(
                        label="Current Trace Status",
                        value=get_current_trace_status(),
                        lines=8,
                    )
                    refresh_btn = gr.Button("🔄 Refresh Status", variant="primary")

                with gr.Column(scale=2):
                    trace_table = gr.Dataframe(
                        headers=[
                            "Trace Name",
                            "Status",
                            "Duration",
                            "Tools",
                            "Start Time",
                        ],
                        value=get_trace_list(),
                        label="Recent Traces",
                    )

            # Auto-refresh
            refresh_btn.click(
                fn=lambda: (get_current_trace_status(), get_trace_list()),
                outputs=[current_status, trace_table],
            )

        with gr.Tab("Trace Details"):
            with gr.Row():
                trace_selector = gr.Dropdown(
                    choices=[t["trace_name"] for t in trace_monitor.traces],
                    label="Select Trace",
                    interactive=True,
                )
                load_btn = gr.Button("Load Details")

            trace_details = gr.Textbox(
                label="Trace Details",
                value="Select a trace to view details",
                lines=20,
                max_lines=30,
            )

            load_btn.click(
                fn=get_trace_details, inputs=[trace_selector], outputs=[trace_details]
            )

        with gr.Tab("Analytics"):
            analytics_text = gr.Textbox(
                label="Tool Usage Analytics", value=get_tool_analytics(), lines=20
            )

            with gr.Row():
                refresh_analytics = gr.Button("🔄 Refresh Analytics")
                export_btn = gr.Button("💾 Export All Traces")

            export_status = gr.Textbox(label="Export Status", visible=False)

            refresh_analytics.click(fn=get_tool_analytics, outputs=[analytics_text])

            export_btn.click(fn=export_traces, outputs=[export_status]).then(
                lambda: gr.update(visible=True), outputs=[export_status]
            )

        with gr.Tab("Trace Visualization"):
            gr.Markdown("### 📊 Visual Trace Flow")

            selected_trace_vis = gr.Dropdown(
                choices=[t["trace_name"] for t in trace_monitor.traces],
                label="Select Trace to Visualize",
            )

            trace_flow = gr.HTML(
                value="<p>Select a trace to visualize the tool flow</p>"
            )

            def create_trace_flow_html(trace_name: str) -> str:
                """Create HTML visualization of trace flow"""
                trace = next(
                    (t for t in trace_monitor.traces if t["trace_name"] == trace_name),
                    None,
                )
                if not trace:
                    return "<p>Trace not found</p>"

                html = ['<div style="font-family: monospace; padding: 20px;">']
                html.append(f"<h3>{trace_name}</h3>")
                html.append(f'<p>Duration: {trace.get("duration_seconds", 0):.2f}s</p>')

                # Tool flow
                html.append(
                    '<div style="display: flex; align-items: center; flex-wrap: wrap;">'
                )
                for i, tool in enumerate(trace.get("tool_calls", [])):
                    if i > 0:
                        html.append('<span style="margin: 0 10px;">→</span>')

                    color = {
                        "analyze_email": "#4CAF50",
                        "extract_order_items": "#2196F3",
                        "search_inventory": "#FF9800",
                        "make_decision": "#9C27B0",
                        "generate_document": "#F44336",
                    }.get(tool["tool"], "#607D8B")

                    html.append(
                        f"""
                        <div style="
                            background: {color};
                            color: white;
                            padding: 10px 15px;
                            border-radius: 5px;
                            margin: 5px;
                            text-align: center;
                        ">
                            <strong>{tool['tool']}</strong>
                        </div>
                    """
                    )

                html.append("</div>")

                # Summary
                if trace.get("summary"):
                    html.append(
                        f'<p style="margin-top: 20px;"><strong>Summary:</strong> {trace["summary"]}</p>'
                    )

                html.append("</div>")
                return "".join(html)

            selected_trace_vis.change(
                fn=create_trace_flow_html,
                inputs=[selected_trace_vis],
                outputs=[trace_flow],
            )

    return dashboard


# Standalone function to launch the dashboard
def launch_trace_dashboard():
    """Launch the trace monitoring dashboard"""
    dashboard = create_trace_dashboard()
    dashboard.launch(share=True, server_name="0.0.0.0", server_port=7861)


if __name__ == "__main__":
    launch_trace_dashboard()
