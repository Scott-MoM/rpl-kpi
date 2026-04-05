import { ComponentType, useEffect, useState } from "react";

type LazyPlotProps = {
  data: unknown;
  layout?: Record<string, unknown>;
  style?: Record<string, unknown>;
  config?: Record<string, unknown>;
};

type PlotTrace = {
  type?: string;
};

export function LazyPlot(props: LazyPlotProps) {
  const [PlotComponent, setPlotComponent] = useState<ComponentType<any> | null>(null);
  const usesGeo = Array.isArray(props.data) && props.data.some((trace) => (trace as PlotTrace)?.type === "scattergeo");

  useEffect(() => {
    let active = true;
    const loader = usesGeo ? import("./plotlyGeoBundle") : import("./plotlyBasicBundle");
    loader.then((module) => {
      if (!active) return;
      setPlotComponent(() => ("PlotlyGeoComponent" in module ? module.PlotlyGeoComponent : module.PlotlyBasicComponent));
    });
    return () => {
      active = false;
    };
  }, [usesGeo]);

  if (!PlotComponent) {
    return <div className="status-panel">Loading chart...</div>;
  }

  return <PlotComponent {...props} />;
}
