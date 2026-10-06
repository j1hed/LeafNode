import iconViewBoxes from '../data/iconViewBoxes.json';

type Props = {
  src: string;
  alt?: string;
  className?: string;
};

type IconViewport = { width: number; height: number; viewBox: number[] };
const viewports: Record<string, IconViewport> = iconViewBoxes;

export default function IconImage({ src, alt = '', className = '' }: Props) {
  const viewport = viewports[src];

  if (!viewport) {
    return <img src={src} alt={alt} className={'icon-image ' + className} draggable={false} />;
  }

  // Frame the visible artwork, with breathing room for its glow.
  // The original PNG stays intact; transparent margins no longer shrink the symbol.
  return (
    <svg className={'icon-image ' + className} viewBox={viewport.viewBox.join(' ')}
      role={alt ? 'img' : undefined} aria-label={alt || undefined} aria-hidden={alt ? undefined : true} focusable="false">
      <image href={src} width={viewport.width} height={viewport.height} />
    </svg>
  );
}
