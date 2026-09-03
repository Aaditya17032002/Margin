import { ImageResponse } from "next/og";

export const alt = "Margin — capture intelligence for government solicitations";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const CLAUSE = [
  "L.3.1  Volume I, Technical, shall not exceed forty (40) pages,",
  "excluding resumes and the cross-reference matrix.",
  "M.2.1  Award will be made to the offeror whose proposal",
  "represents the best value to the Agency.",
];

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#F6F2E9",
          color: "#211D17",
          padding: 72,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "space-between" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                fontSize: 20,
                letterSpacing: 6,
                textTransform: "uppercase",
                color: "#8A8072",
                display: "flex",
              }}
            >
              Margin
            </div>
            <div style={{ fontSize: 68, lineHeight: 1.12, marginTop: 28, maxWidth: 620, display: "flex" }}>
              Read the solicitation before you commit a team to it.
            </div>
          </div>
          <div style={{ fontSize: 26, color: "#5B5347", maxWidth: 560, display: "flex" }}>
            Every finding carries the page, the section, and the line it stands on.
          </div>
        </div>

        {/* The leaf: a page with its margin rule and one highlighted clause. */}
        <div
          style={{
            width: 400,
            display: "flex",
            flexDirection: "column",
            background: "#FCFAF4",
            border: "1px solid #D6CBB3",
            borderRadius: 10,
            padding: "44px 34px",
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 60,
              top: 0,
              bottom: 0,
              width: 1,
              background: "#9B2D28",
              opacity: 0.3,
              display: "flex",
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 14, paddingLeft: 42 }}>
            {CLAUSE.map((line, i) => (
              <div
                key={i}
                style={{
                  fontSize: 17,
                  lineHeight: 1.5,
                  color: i < 2 ? "#211D17" : "#8A8072",
                  background: i < 2 ? "#F6ECD6" : "transparent",
                  padding: i < 2 ? "3px 6px" : "3px 0",
                  borderRadius: 3,
                  display: "flex",
                }}
              >
                {line}
              </div>
            ))}
          </div>
          <div
            style={{
              marginTop: 40,
              marginLeft: 42,
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 15,
              color: "#5B5347",
            }}
          >
            <div style={{ width: 10, height: 10, borderRadius: 5, background: "#3F6B5C", display: "flex" }} />
            Page 14 · Section L.3.1
          </div>
        </div>
      </div>
    ),
    size,
  );
}
