import plotly.graph_objs as go

mydict = {}
mydict['x'] = [1]
mydict['y'] = [1]

g = go.Scatter(mydict)
print(g['x'])