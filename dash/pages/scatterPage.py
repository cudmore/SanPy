# scatter layout widget

import pandas as pd

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc

import myDashUtils

def getScatterPageLayout(statDict):
	print('scatterPage.getScatterPageLayout()')
	#print('  statDict:', statDict)

	boxBorder = 2

	statsDf = pd.DataFrame(columns=['idx', 'stat'])
	statsDf['idx'] = [i for i in range(len(statDict.keys()))]
	statsDf['stat'] = [x for x in statDict.keys()]

	scatterPageLayout = html.Div(
		[
			dbc.Row(
				[
				dbc.Col(
					html.Div([
						html.Label('X-Stat'),
						myDashUtils.makeTable('x-stat-table', statsDf, height=180, defaultRow=0)
					]) # div
					,width=3,style={"border":boxBorder}
				), # col

				dbc.Col(
					html.Div([
						html.Label('Y-Stat'),
						myDashUtils.makeTable('y-stat-table', statsDf, height=180, defaultRow=0)
					]) # div
					,width=3,style={"border":boxBorder}
				), # col

				# plot
				dbc.Col(
					html.Div([
						dcc.Graph(id='life-exp-vs-gdp')
					])
					,width=6,style={"border":boxBorder}
				), # col
				]
			), # row
		], className = 'container') # outerdiv

	#
	return scatterPageLayout
