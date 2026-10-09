"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { /* A reporting provider can be connected here. */ }
  render() {
    return this.state.failed
      ? <main className="p-8">We could not load this page. Refresh and try again.</main>
      : this.props.children;
  }
}
