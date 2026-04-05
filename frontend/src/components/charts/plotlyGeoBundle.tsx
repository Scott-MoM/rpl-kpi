import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js/lib/core";

import scattergeo from "plotly.js/lib/scattergeo";

Plotly.register([scattergeo]);

export const PlotlyGeoComponent = createPlotlyComponent(Plotly);
