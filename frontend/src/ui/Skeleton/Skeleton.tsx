import React from 'react';

export function Skeleton({
  width = '100%',
  height = 12,
  radius = 10,
  style,
  className,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number;
  style?: React.CSSProperties;
  className?: string;
}) {
  return (
    <div
      className={['rc-skeleton', className].filter(Boolean).join(' ')}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

export function SkeletonLines({
  lines = 3,
  lineHeight = 12,
  gap = 8,
  lastLineWidth = '70%',
}: {
  lines?: number;
  lineHeight?: number;
  gap?: number;
  lastLineWidth?: number | string;
}) {
  const items = Array.from({ length: Math.max(1, lines) });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {items.map((_, idx) => (
        <Skeleton
          key={idx}
          height={lineHeight}
          width={idx === items.length - 1 ? lastLineWidth : '100%'}
          radius={10}
        />
      ))}
    </div>
  );
}
