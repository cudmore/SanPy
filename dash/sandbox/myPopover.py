import dash
import dash_daq as daq
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

defaultColor = '#000000'

colorPicker = html.Div([
    daq.ColorPicker(
        id='my-color-picker',
        label='',
        value=defaultColor
    ),
    html.Div(id='color-picker-output')
])

popover = html.Div(
    [
        html.P(
            ["Click on the word ", html.Span("popover", id="popover-target")]
        ),
        dbc.Popover(
            [
                #dbc.PopoverHeader("Popover header"),
                #dbc.PopoverBody("Popover body"),
                colorPicker,
                dbc.Button("OK", color="primary", outline=True, size="sm", id='ok-color-button'),
                dbc.Button("Cancel", color="primary", outline=True, size="sm", id='cancel-color-button'),
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

app.layout = html.Div([popover])

@app.callback(
    Output("popover", "is_open"),
    [Input("popover-target", "n_clicks"), Input('ok-color-button', 'n_clicks')],
    [State("popover", "is_open"), State('my-color-picker', 'value')],
)
def toggle_popover(n_clicks, ok_n_clicks, is_open, colorValue):
    print('toggle_popover() n_clicks:', n_clicks, 'ok_n_clicks:', ok_n_clicks, 'is_open:', is_open, 'colorValue:', colorValue)
    if ok_n_clicks or n_clicks:
        defaultColor = colorValue
        return not is_open
    return is_open

@app.callback(
    Output('color-picker-output', 'children'),
    [Input('ok-color-button', 'n_clicks')],
    [State('my-color-picker', 'value'), State("popover", "is_open")])
def update_color(n_clicks, value, is_open):
    print('update_color() value:', value)
    return '' #'The selected color is {}.'.format(value)

  
if __name__ == '__main__':

	app.run_server(debug=True)
