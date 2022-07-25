# -*- coding: utf-8 -*-
import dash
import dash_auth
from dash import dcc
from dash import html
from dash import Input,Output,callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go


#Mapbox Token Setup
mapBoxToken = 'pk.eyJ1IjoiamFja2x1byIsImEiOiJjajNlcnh3MzEwMHZtMzNueGw3NWw5ZXF5In0.fk8k06T96Ml9CLGgKmk81w'
import plotly.express as px
px.set_mapbox_access_token(mapBoxToken)




external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

VALID_USERNAME_PASSWORD_PAIRS = {
    'test': 'visual'
}

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

app.title = 'HRM Facilities Footprint'


# Collect Datasets
dim = pd.read_csv('finFacMap.csv')

#Filter Dataframe to display buildings with at least 3 buildings in the same property category
d=dim.OCC_USE.value_counts()>2
df=dim[dim.OCC_USE.isin(d[d].index)].copy()


#impute null values in the SQFT column with the mean of the value from the same Occupancy Use property types
for i in df.index:
    if pd.isnull(df.loc[i].TOTAL_SQFT):
        df.loc[i,'TOTAL_SQFT']= df[df.OCC_USE==df.loc[i].OCC_USE].TOTAL_SQFT.mean()

df.rename(columns={"OCC_USE": "Property Use"}, inplace=True)

#get consumption meter data
m=pd.read_csv('juneConsumption2022.csv',parse_dates=['End Date'])

mapfig = px.scatter_mapbox(df, lat="lat", lon="long",
                           size="TOTAL_SQFT",
                           color="Property Use",
                           color_continuous_scale=px.colors.qualitative.D3,
                           hover_name=df['Portfolio Manager Property Name'],
                           hover_data={'Property Use':True,'lat':False,'long':False},
                           # hovertext=df['Portfolio Manager Property Name'],
                           # hovertemplate='<i><b>prop<b></i>',
                           size_max=25,
                           title='HRM Facilities Map Picker',
                           center = {'lat':44.6495565,'lon':-63.5877328},

                        custom_data = ['BL_ID'],
                        mapbox_style='streets',
                        zoom=10)

mapfig.update_layout(margin=dict(l=5, r=5, b=5, t=25))

app.layout =  dbc.Container([
                # html.Div([dcc.Graph(id='map',figure=mapfig)],style={'height': '500px', 'width': '50%'}),
                # html.Div(id='context',style={'height': '500px', 'width': '40%'})
                    dbc.Row(dcc.Graph(id='map',figure=mapfig)),
                    dcc.Loading(html.Div(id="context"), type="cube")
],fluid=True)


#clickData, selectedData

@app.callback(
    [Output("context","children")],
    [Input("map", "clickData"),
     Input("map", "selectedData")])
def update_line_chart(d1,d2):
    # if d1==None:
    #     return [str(d2)]
    # else:return [str(d1)]

    if callback_context.triggered[0]['value'] == None:
        return [html.Div([html.H6('Click on the Bubble or select multiple by using Box or Lasso selection')])]

    if callback_context.triggered[0]['prop_id'] == 'map.clickData':
        clickedDF = m[m['HRM Building ID'] == callback_context.triggered[0]['value']['points'][0]['customdata'][0]].copy()
        clickedDF['month'] = clickedDF['End Date'].dt.month
        clickedDF['month_name'] = clickedDF['End Date'].dt.month_name()
        clickedDF['year'] = clickedDF['End Date'].dt.year
        # create a simple line chart

        line = clickedDF.groupby(by=['End Date']).sum()[['Consumption(kWh)']]

        quarterly = line.rolling(3, center=True).mean()

        yearly = line.rolling(12, center=True).mean()

        Linefig = go.Figure()
        Linefig.add_trace(go.Scatter(x=line.index, y=line['Consumption(kWh)'],
                                     mode='lines',
                                     marker=dict(color="#341f97"),
                                     name='Actual'))
        Linefig.add_trace(go.Scatter(x=quarterly.index, y=quarterly['Consumption(kWh)'],
                                     mode='lines+markers',  # fillcolor="#01a3a4",
                                     marker=dict(color="#74c9ed"),
                                     name='Quarterly (avg)'))
        Linefig.add_trace(go.Scatter(x=yearly.index, y=yearly['Consumption(kWh)'],
                                     mode='markers',  # fillcolor="#8395a7",
                                     marker=dict(color="#72fc96"),
                                     name='Yearly (avg)'))

        Linefig.update_layout(xaxis_rangeslider_visible=True,
                              margin=dict(l=5, r=5, b=5, t=30),
                              template = "ggplot2",  title= 'kWh used at ' +callback_context.triggered[0]['value']['points'][0]['hovertext'])
        Linefig.update(layout_showlegend=False)
        Lfig = dcc.Graph(id='L', figure=Linefig)


        # Create a 3D line chart
        clickedDF3D = clickedDF.groupby(by=['month', 'year', 'Energy Type']).sum().reset_index('month').copy()
        clickedDF3D.reset_index(inplace=True)
        fig = px.line_3d(clickedDF3D, x='year', y='month', z='Consumption(kWh)',
                  color='year'
                         ,title = 'Yearly kWH variation at '+callback_context.triggered[0]['value']['points'][0]['hovertext'],
                         #template="plotly_dark"
                         )


        fig.update_layout(
            autosize = True,
            xaxis_title="X Axis Title",
            yaxis_title="Y Axis Title",
            legend_title="Year",
            margin=dict(l=5, r=5, b=5, t=30),
            showlegend=False,
            # font=dict(
            #     family="Monaco, monospace",
            #     size=13,
            #     color="RebeccaPurple"
            # )
        )

        Dfig = dcc.Graph(id='D', figure = fig)


        Sunfig = px.sunburst(clickedDF,
                     path=['year', 'Season', 'Energy Type'],
                     values='Consumption(kWh)', color = 'Energy Type',
                     color_discrete_map = {'Electricity':'#61ff7b', 'Natural Gas': '#93cafc', 'Fuel Oil': '#4e7855', 'Propane':'#8e8af2' },
                     hover_data={'Consumption(kWh)':True },
                     title='Seasonal kWh by Energy Source',
                     maxdepth =3,
                      #height=700,
                     # width = 800,
                     )
        Sunfig.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        Sfig= dcc.Graph(id='S', figure = Sunfig)

        YSunfig = px.sunburst(clickedDF,
                     path=['year', 'Energy Type'],
                     values='Consumption(kWh)', color = 'Energy Type',
                     color_discrete_map = {'Electricity':'#61ff7b', 'Natural Gas': '#93cafc', 'Fuel Oil': '#4e7855', 'Propane':'#8e8af2' },
                     hover_data={'Consumption(kWh)':True },
                     title='Yearly kWh by Energy Source',
                     maxdepth =2,
                      #height=700,
                     # width = 800,
                     )
        YSunfig.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        YSfig= dcc.Graph(id='YS', figure = YSunfig)


        opiefig = px.pie(clickedDF, values='Consumption(kWh)', names='Energy Type', color ='Energy Type',
                         color_discrete_map = {'Electricity':'#61ff7b', 'Natural Gas': '#93cafc', 'Fuel Oil': '#4e7855', 'Propane':'#8e8af2' }, title='Total Energy sources (in kWh)')
        opiefig.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        opiefig.update(layout_showlegend = False)
        opfig = dcc.Graph(id='op', figure=opiefig)




        # Emmissions

        anim = clickedDF.groupby(by=['year']).sum().reset_index()[
            ['year', 'Emission_SOx', 'Emission_PM',
             'Emission_NOx', 'Emission_VOC', 'Emission_CO', 'Emission_NH3','GHG&CAC']]

        animate = anim.melt(id_vars=["year"],
                            var_name="Types",
                            value_name="Value")
        clickedDF['ym'] = clickedDF['End Date'].dt.strftime('%Y-%m')
        co2 = clickedDF.groupby(by=['ym']).sum().reset_index()[
            ['ym', 'GHG&CAC']]

        co2Pie = px.line(co2, y='GHG&CAC', x='ym'
                         , title='GHG & CAC Emissions(Kg): '+callback_context.triggered[0]['value']['points'][0]['hovertext']
                         , line_shape= 'spline')
        co2Pie['data'][0]['line']['color']='firebrick'
        co2Pie['data'][0]['line']['width']=2
        co2Pie.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        co2Pie.update(layout_showlegend = False)
        co2fig = dcc.Graph(id='op', figure=co2Pie)

        emBar = px.bar(animate[~animate['Types'].isin(['Emission_CO2','GHG&CAC'])], x="year", y="Value", color="Types", title="Emissions(Excluding CO2)")
        emBar.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        emfig = dcc.Graph(id='op', figure=emBar)






        #Category based onalysis

        # build Pie chart of the same categories with a pull out
        CategoryDF= m[m['HRM Building ID'].isin(dim[dim.OCC_USE == callback_context.triggered[0]['value']['points'][0]['customdata'][1]]['BL_ID'].values)].copy()
        CategoryDF['year'] = CategoryDF['End Date'].dt.year
        CategoryDF['ym'] = CategoryDF['End Date'].dt.strftime('%Y-%m')
        categoryGroup = CategoryDF.groupby(by=['HRM Building ID']).sum().reset_index('HRM Building ID')[['HRM Building ID','Consumption(kWh)','GHG&CAC']]
        categoryGroup.rename(columns={'HRM Building ID': 'BL_ID'}, inplace=True)
        pie =categoryGroup.merge(dim[['BL_ID', 'Portfolio Manager Property Name','TOTAL_SQFT']], on=['BL_ID'], how='left').copy()
        pie['Pull'] = np.where(pie['BL_ID'] == callback_context.triggered[0]['value']['points'][0]['customdata'][0], 0.5, 0)

        piefig= go.Figure(data=[go.Pie(labels=pie['Portfolio Manager Property Name'].values, values=pie['Consumption(kWh)'].values, pull=pie['Pull'].values)])
        piefig.update_traces(hoverinfo='label+percent', textinfo='none',marker=dict(line=dict(color='#000000', width=1)))
        piefig.update(layout_title_text='kWh Share within '+callback_context.triggered[0]['value']['points'][0]['customdata'][1],
                   layout_showlegend=False)
        piefig.update_layout(margin=dict(l=5, r=5, b=5, t=30))

        Pfig = dcc.Graph(id='P', figure=piefig)

        piefigE= go.Figure(data=[go.Pie(labels=pie['Portfolio Manager Property Name'].values, values=pie['GHG&CAC'].values, pull=pie['Pull'].values)])
        piefigE.update_traces(hoverinfo='label+percent', textinfo='none',marker=dict(line=dict(color='#000000', width=1)))
        piefigE.update(layout_title_text='GHG&CAC Share within '+callback_context.triggered[0]['value']['points'][0]['customdata'][1],
                   layout_showlegend=False)
        piefigE.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        PEfig = dcc.Graph(id='PE', figure=piefigE)


        #Emission animate
        categoryAnimateGroup = CategoryDF[CategoryDF['year']!=2022].groupby(by=['HRM Building ID','year']).sum().reset_index(['HRM Building ID','year'])
        categoryAnimateGroup.rename(columns={'HRM Building ID': 'BL_ID'}, inplace=True)
        categoryAnimate = categoryAnimateGroup.merge(dim[['BL_ID', 'Portfolio Manager Property Name', 'TOTAL_SQFT']],
                                                     on=['BL_ID'], how='left').copy()
        catAnimate = px.scatter(categoryAnimate, x="TOTAL_SQFT", y="GHG&CAC", animation_frame="year", color ="Portfolio Manager Property Name",
           size="Emission_consumption", size_max=35, title='Animated GHG&CAC Emission for '+callback_context.triggered[0]['value']['points'][0]['customdata'][1])
        catAnimate.update_layout(margin=dict(l=5, r=5, b=5, t=30))
        catAnimate.update(layout_showlegend = False)
        catAnimatefig = dcc.Graph(id='AC', figure=catAnimate)



        # line chart for comparable kWh/SqFt across similar category
        categoryAnimate = categoryAnimateGroup.merge(dim[['BL_ID', 'Portfolio Manager Property Name', 'TOTAL_SQFT']],
                                                     on=['BL_ID'], how='left').copy()


        # lineDF = CategoryDF.groupby(by=['HRM Building ID','End Date']).sum().reset_index()[['HRM Building ID','Consumption(kWh)','End Date']]
        # lineDF.rename(columns={'HRM Building ID': 'BL_ID'}, inplace=True)
        # line = lineDF.merge(dim[['BL_ID', 'Portfolio Manager Property Name', 'TOTAL_SQFT']], on=['BL_ID'], how='left')



        # Lfig = dcc.Graph(id='L', figure=Linefig)

        return [html.Div([
                    html.Div(html.H3(callback_context.triggered[0]['value']['points'][0]['hovertext']), style={'textAlign': 'center'}),
                    html.Div(html.H4('1. Energy consumption patterns'), style={'textAlign': 'center'}),
                    html.Div([
                        html.Div(Lfig, style={'height': '40%', 'width': '60%', 'display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        html.Div(style={'height': '40%', 'width': '3%', 'display': 'inline-block'}),
                        html.Div(Dfig, style={'height': '40%', 'width': '35%', 'display': 'inline-block'})
                    ], style={'width': '100%', 'display': 'inline-block', 'border':'dotted','borderWidth':'1px'}),
                    html.Div(html.H4('2. Energy sources Breakdown'), style={'textAlign': 'center'}),
                    html.Div([
                        html.Div(style={'height': '40%', 'width': '5%', 'display': 'inline-block'}),
                        html.Div(opfig, style={'height': '40%','width':'28%','display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px' }),
                        html.Div(style={'height': '40%', 'width': '5%','display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        html.Div(YSfig, style={'height': '40%','width':'28%', 'display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        html.Div(style={'height': '40%', 'width': '5%','display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        html.Div(Sfig, style={'height': '40%','width':'28%', 'display': 'inline-block'})
                    ], style={'width':'100%','display': 'inline-block', 'border':'dotted','borderWidth':'1px'}),
                    html.Div(html.H4('3. GHG & CAC emissions'), style={'textAlign': 'center'}),
                    html.Div([
                        html.Div(co2fig, style={'height': '40%', 'width': '50%', 'display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        html.Div(style={'height': '40%', 'width': '3%', 'display': 'inline-block'}),
                        html.Div(emfig, style={'height': '40%', 'width': '45%', 'display': 'inline-block'})
                    ], style={'width': '100%', 'display': 'inline-block', 'border':'dotted','borderWidth':'1px'}),
                    html.Div(html.H4('4. Consumption & Emission compared to similar properties'), style={'textAlign': 'center'}),
                    html.Div([
                        html.Div(Pfig, style={'height': '40%', 'width': '25%', 'display': 'inline-block', 'border':'dotted','borderWidth':'0px 1px 0px 0px'}),
                        # html.Div(style={'height': '40%', 'width': '1%', 'display': 'inline-block'}),
                        html.Div(PEfig,
                                 style={'height': '40%', 'width': '25%', 'display': 'inline-block', 'border': 'dotted',
                                        'borderWidth': '0px 1px 0px 0px'}),
                        # html.Div(style={'height': '40%', 'width': '1%', 'display': 'inline-block'}),
                        html.Div(catAnimatefig, style={'height': '100%', 'width': '49%', 'display': 'inline-block'}),
                    ], style={'width': '100%', 'display': 'inline-block', 'border':'dotted','borderWidth':'1px'})
                    # dbc.Col(Lfig, width={'size': 5})
                ])]

    elif callback_context.triggered[0]['prop_id'] == 'map.selectedData':
        dc = []
        for x in callback_context.triggered[0]['value']['points']:
            lineDF = m[m['HRM Building ID'] == x['customdata'][0]].copy()
            line = lineDF.groupby(by=['End Date']).sum()[['Consumption(kWh)']]

            quarterly = line.rolling(3, center=True).mean()

            yearly = line.rolling(12, center=True).mean()

            Linefig = go.Figure()
            Linefig.add_trace(go.Scatter(x=line.index, y=line['Consumption(kWh)'],
                                         mode='lines',
                                         marker=dict(color="#341f97"),
                                         name='Actual'))
            Linefig.add_trace(go.Scatter(x=quarterly.index, y=quarterly['Consumption(kWh)'],
                                         mode='lines+markers',  # fillcolor="#01a3a4",
                                         marker=dict(color="#d1e39a"),
                                         name='Quarterly'))
            Linefig.add_trace(go.Scatter(x=yearly.index, y=yearly['Consumption(kWh)'],
                                         mode='markers',  # fillcolor="#8395a7",
                                         marker=dict(color="#72fc96"),
                                         name='Yearly'))

            Linefig.update_layout(xaxis_rangeslider_visible=True, title = x['hovertext'])


            dc.append(dcc.Graph(id = x['hovertext'], figure = Linefig ))


        return [html.Div(dc)]

if __name__ == '__main__':
    app.run_server(debug=False)