import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

export const ChartComponent = ({ data, colors = {} }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight 
        });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor || '#151924' },
        textColor: colors.textColor || '#d1d5db',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });
    
    const newSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    newSeries.setData(data);

    // Add EMA 21
    const emaSeries = chart.addLineSeries({
      color: '#fbbf24', // Amber/Yellow
      lineWidth: 2,
      title: 'EMA 21',
    });
    const emaData = data
      .filter(d => d.ema_21)
      .map(d => ({ time: d.time, value: d.ema_21 }));
    emaSeries.setData(emaData);

    // Add Support (Green dashed)
    const supportSeries = chart.addLineSeries({
      color: '#4ade80', // Green
      lineWidth: 1,
      lineStyle: 2, // Dashed
      title: 'Support',
    });
    const supportData = data
      .filter(d => d.support)
      .map(d => ({ time: d.time, value: d.support }));
    supportSeries.setData(supportData);

    // Add Resistance (Red dashed)
    const resistanceSeries = chart.addLineSeries({
      color: '#f87171', // Red
      lineWidth: 1,
      lineStyle: 2, // Dashed
      title: 'Resistance',
    });
    const resistanceData = data
      .filter(d => d.resistance)
      .map(d => ({ time: d.time, value: d.resistance }));
    resistanceSeries.setData(resistanceData);

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => handleResize());
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [data, colors]);

  return (
    <div
      ref={chartContainerRef}
      className="w-full h-full"
    />
  );
};
