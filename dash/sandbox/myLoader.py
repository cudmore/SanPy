# -*- coding: utf-8 -*-
import dash
import dash_html_components as html
import dash_core_components as dcc
import time

from dash.dependencies import Input, Output, State

app = dash.Dash(__name__)

app.scripts.config.serve_locally = True

app.layout = html.Div(
    children=[
        html.H3("Edit text input to see loading state"),
        dcc.Input(id="input-1", value='Input triggers local spinner'),
        dcc.Loading(id="loading-1", children=[html.Div(id="loading-output-1")], type="default"),
        html.Div(
            [
                dcc.Input(id="input-2", value='Input triggers nested spinner'),
                dcc.Loading(
                    id="loading-2",
                    children=[html.Div([html.Div(id="loading-output-2")])],
                    type="circle",
                )
            ]
        ),
    ],
)

@app.callback(Output("loading-output-1", "children"), [Input("input-1", "value")])
def input_triggers_spinner(value):
    time.sleep(3)
    return value


@app.callback(Output("loading-output-2", "children"), [Input("input-2", "value")])
def input_triggers_nested(value):
    time.sleep(3)
    return value


if __name__ == "__main__":
    app.run_server(debug=False)
