import type { CSSProperties } from "react";

import type { TextNode } from "../types";

type TextNodeViewProps = {
  node: TextNode;
};

export function TextNodeView({ node }: TextNodeViewProps) {
  const style: CSSProperties = {};
  let className = "em-text";

  for (const mark of node.marks ?? []) {
    if (mark.type === "bold") {
      className += " em-text-bold";
    }
    if (mark.type === "fontSize") {
      style.fontSize = `${mark.value}px`;
    }
  }

  return (
    <span className={className} style={style} data-node-id={node.id}>
      {node.text}
    </span>
  );
}
