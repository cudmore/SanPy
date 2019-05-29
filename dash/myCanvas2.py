import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
from dash_canvas import DashCanvas
import json
from dash_table import DataTable

app = dash.Dash(__name__)

filename = 'https://upload.wikimedia.org/wikipedia/commons/e/e4/Mitochondria%2C_mammalian_lung_-_TEM_%282%29.jpg'
canvas_width = 500

columns = ['type', 'width', 'height', 'scaleX', 'strokeWidth', 'path']

app.layout = html.Div([
    html.H6('Draw on image and press Save to show annotations geometry'),
    DashCanvas(id='annot-canvas',
               lineWidth=5,
               filename=filename,
               width=canvas_width,
               ),
    DataTable(id='table',
              style_cell={'textAlign': 'left'},
              columns=[{"name": i, "id": i} for i in columns]),
    ])


@app.callback(Output('table', 'data'),
              [Input('annot-canvas', 'json_data')])
def update_data(string):
    if string:
        data = json.loads(string)
    else:
        raise PreventUpdate
    return data['objects'][1:]


if __name__ == '__main__':
    app.run_server(debug=True)
