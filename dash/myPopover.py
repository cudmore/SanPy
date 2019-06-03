import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

popover = html.Div(
    [
        html.P(
            ["Click on the word ", html.Span("popover", id="popover-target")]
        ),
        dbc.Popover(
            [
                dbc.PopoverHeader("Popover header"),
                dbc.PopoverBody("Popover body"),
            ],
            id="popover",
            is_open=False,
            target="popover-target",
            delay={'show':100, 'hide':500},
        ),
    ]
)

tooltip = html.Div(
    [
        html.P(
            [
                "I wonder what ",
                html.Span(
                    "floccinaucinihilipilification", id="tooltip-target"
                ),
                " means?",
            ]
        ),
        dbc.Tooltip(
            "Noun: rare, "
            "the action or habit of estimating something as worthless.",
            target="tooltip-target",
        ),
    ]
)

app.layout = tooltip

'''
@app.callback(
    Output("popover", "is_open"),
    [Input("popover-target", "n_clicks")],
    [State("popover", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open
'''
    
if __name__ == '__main__':

	app.run_server(debug=True)
