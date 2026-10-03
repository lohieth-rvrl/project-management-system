import { useEffect, useRef } from "react";
import * as echarts from "echarts";

// Thin wrapper: pass an ECharts option object, it handles init/resize/dispose.
export default function Chart({ option, height = 280 }) {
  const ref = useRef(null);
  const inst = useRef(null);

  useEffect(() => {
    inst.current = echarts.init(ref.current);
    const onResize = () => inst.current && inst.current.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      inst.current.dispose();
      inst.current = null;
    };
  }, []);

  useEffect(() => {
    if (inst.current) inst.current.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ height, width: "100%" }} />;
}
