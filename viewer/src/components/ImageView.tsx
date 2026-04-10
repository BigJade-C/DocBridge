import type { ImageNode } from "../types";

type ImageViewProps = {
  node: ImageNode;
  selected?: boolean;
  onSelect?: (imageId: string) => void;
};

function isBrowserLoadableSource(src: string | null | undefined): boolean {
  if (!src) {
    return false;
  }
  return (
    src.startsWith("/") ||
    src.startsWith("./") ||
    src.startsWith("../") ||
    src.startsWith("http://") ||
    src.startsWith("https://") ||
    src.startsWith("data:")
  );
}

export function ImageView({ node, selected = false, onSelect }: ImageViewProps) {
  const src = node.attrs?.src;
  const alt = node.attrs?.alt ?? "Image";
  const width = node.attrs?.width ?? undefined;
  const height = node.attrs?.height ?? undefined;
  const imageSrc = src ?? undefined;
  const className = `em-image${selected ? " is-selected" : ""}`;

  if (isBrowserLoadableSource(src)) {
    return (
      <figure
        className={className}
        data-node-id={node.id}
        data-testid={`image-${node.id}`}
        onClick={() => onSelect?.(node.id)}
      >
        <img src={imageSrc} alt={alt} width={width} height={height} />
      </figure>
    );
  }

  return (
    <figure
      className={`${className} em-image-placeholder`}
      data-node-id={node.id}
      data-testid={`image-${node.id}`}
      onClick={() => onSelect?.(node.id)}
    >
      <div className="em-image-meta">
        <strong>{alt}</strong>
        <span>src: {src ?? "(missing)"}</span>
        <span>
          size: {width ?? "?"} × {height ?? "?"}
        </span>
      </div>
    </figure>
  );
}
