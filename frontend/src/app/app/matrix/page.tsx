import type { Metadata } from "next";

import { MatrixView } from "@/components/views/matrix";

export const metadata: Metadata = {
  title: "Compliance matrix",
  description: "Every shall, should, and may across the portfolio, each tied to its clause.",
};

export default function MatrixPage() {
  return <MatrixView />;
}
