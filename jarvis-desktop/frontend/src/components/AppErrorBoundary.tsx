import React from 'react';

interface AppErrorBoundaryProps {
  children: React.ReactNode;
}

interface AppErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

export default class AppErrorBoundary extends React.Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = {
    hasError: false,
    errorMessage: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error.message,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('App shell crashed:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      errorMessage: null,
    });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex h-full w-full items-center justify-center bg-jarvis-bg px-6 text-jarvis-text">
        <div className="w-full max-w-lg rounded-2xl border border-red-500/30 bg-black/30 p-8 shadow-2xl shadow-red-500/10">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-red-400">
            Interface Recovery
          </p>
          <h1 className="mt-3 text-3xl font-bold text-white">
            The assistant UI hit an unexpected error.
          </h1>
          <p className="mt-3 text-sm leading-6 text-jarvis-textMuted">
            The app stayed alive, but this screen section needs a reset. You can retry the view
            or reload the page if the same issue keeps happening.
          </p>
          {this.state.errorMessage && (
            <p className="mt-4 rounded-xl border border-white/10 bg-white/5 px-4 py-3 font-mono text-xs text-jarvis-textMuted">
              {this.state.errorMessage}
            </p>
          )}
          <div className="mt-6 flex gap-3">
            <button
              onClick={this.handleReset}
              className="rounded-xl bg-jarvis-accentPink px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-jarvis-accentPink/80"
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-jarvis-text transition-colors hover:bg-white/10"
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
