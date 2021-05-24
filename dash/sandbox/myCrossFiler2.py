import dash
import dash_core_components as dcc
import dash_html_components as html
import datetime
import json
import random
from dash.dependencies import Output, Input, State


app = dash.Dash()
app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})  # noqa: E501

graph_names = ["foo", "bar", "baz"]


def random_points(length):
    return [random.randint(5, 10) for _ in range(length)]


graph_figures = [{'data': [{'x': [0, 1, 2], 'y': random_points(3), 'type': 'bar', 'name': '{} widgets'.format(name)},
                           {'x': [0, 1, 2], 'y': random_points(3), 'type': 'bar', 'name': '{} trinkets'.format(name)}],
                  'layout': {'title': name}} for name in graph_names]

pre_style = {"backgroundColor": "#ddd", "fontSize": 20, "padding": "10px", "margin": "10px"}

app.layout = html.Div(children=[
    dcc.Graph(id='foo', figure=graph_figures[0], className="four columns"),
    dcc.Graph(id='bar', figure=graph_figures[1], className="four columns"),
    dcc.Graph(id='baz', figure=graph_figures[2], className="four columns"),
    html.Label('Foo clickDatas'),
    html.Pre(id='foo-click-datas', style=pre_style),
    html.Label('Bar clickDatas'),
    html.Pre(id='bar-click-datas', style=pre_style),
    html.Label('Baz clickDatas'),
    html.Pre(id='baz-click-datas', style=pre_style),
    html.Label('Most recent clickdata'),
    html.Pre(id='update-on-click-data', style=pre_style),
])


for name in graph_names:
    @app.callback(Output('{}-click-datas'.format(name), 'children'),
                  [Input(name, 'clickData')],
                  [State('{}-click-datas'.format(name), 'id'), State('{}-click-datas'.format(name), 'children')])
    def graph_clicked(click_data, clicked_id, children):
        if not children:
            children = []
        if click_data is None:
            return []
        else:
            click_data["time"] = int(datetime.datetime.now().timestamp())
            click_data["id"] = clicked_id
            children.append(json.dumps(click_data) + "\n")
            children = children[-3:]
            return children


@app.callback(Output('update-on-click-data', 'children'),
              [Input("{}-click-datas".format(name), 'children') for name in graph_names])
def determine_last_click(*clickdatas):
    most_recent = None
    for clickdata in clickdatas:
        if clickdata:
            last_child = json.loads(clickdata[-1].strip())
            if clickdata and (most_recent is None or int(last_child['time']) > json.loads(most_recent)['time']):
                most_recent = json.dumps(last_child)
    return most_recent


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True)