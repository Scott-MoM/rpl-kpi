import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js/lib/core";

import bar from "plotly.js/lib/bar";
import pie from "plotly.js/lib/pie";
import scatter from "plotly.js/lib/scatter";

Plotly.register([bar, pie, scatter]);

export const PlotlyBasicComponent = createPlotlyComponent(Plotly);
