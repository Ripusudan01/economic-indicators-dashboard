import React from "react";

const paths = {
  alert: <><path d="M10.3 3.9 2.5 17.4a1.8 1.8 0 0 0 1.6 2.6h15.8a1.8 1.8 0 0 0 1.6-2.6L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4m0 4h.01" /></>,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
  key: <><circle cx="8" cy="15" r="4" /><path d="m11 12 9-9m-4 4 3 3m-6-1 3 3" /></>,
  ruler: <><path d="m4 16 12-12 4 4L8 20H4z" /><path d="m14 6 2 2m-5 1 2 2m-5 1 2 2m-5 1 2 2" /></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M5.6 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.4-3" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-9h.01" /></>,
};

export default function Icon({ name, size = 16, className = "" }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
