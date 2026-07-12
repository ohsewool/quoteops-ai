import { render, screen } from "@testing-library/react";

import App from "./App.jsx";

describe("V2 foundation placeholder", () => {
  it("identifies the repository foundation without pretending to be a product screen", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "QuoteOps AI V2 foundation" })).toBeInTheDocument();
    expect(screen.getByText("Repository and security foundation")).toBeInTheDocument();
  });
});
