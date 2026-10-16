import React from "react";

// Circular India Flag SVG
export function IndiaFlag({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={{ borderRadius: "50%", flexShrink: 0 }}>
      <rect width="32" height="10.66" fill="#FF9933" />
      <rect y="10.66" width="32" height="10.66" fill="#FFFFFF" />
      <rect y="21.32" width="32" height="10.66" fill="#138808" />
      <circle cx="16" cy="16" r="4.5" fill="none" stroke="#000080" strokeWidth="0.8" />
      <circle cx="16" cy="16" r="1.2" fill="#000080" />
    </svg>
  );
}

// Circular US Flag SVG
export function USFlag({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={{ borderRadius: "50%", flexShrink: 0 }}>
      <rect width="32" height="32" fill="#B22234" />
      <rect y="4.5" width="32" height="4.5" fill="#FFFFFF" />
      <rect y="13.5" width="32" height="4.5" fill="#FFFFFF" />
      <rect y="22.5" width="32" height="4.5" fill="#FFFFFF" />
      <rect width="14" height="18" fill="#3C3B6E" />
      <circle cx="4" cy="5" r="1" fill="#FFFFFF" />
      <circle cx="10" cy="5" r="1" fill="#FFFFFF" />
      <circle cx="7" cy="9" r="1" fill="#FFFFFF" />
      <circle cx="4" cy="13" r="1" fill="#FFFFFF" />
      <circle cx="10" cy="13" r="1" fill="#FFFFFF" />
    </svg>
  );
}

// Circular Globe Icon SVG
export function GlobeIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" style={{ borderRadius: "50%", flexShrink: 0 }}>
      <circle cx="16" cy="16" r="15" fill="#1e3a8a" stroke="#38bdf8" strokeWidth="1" />
      <ellipse cx="16" cy="16" rx="8" ry="15" fill="none" stroke="#60a5fa" strokeWidth="1" />
      <line x1="1" y1="16" x2="31" y2="16" stroke="#60a5fa" strokeWidth="1" />
      <line x1="5" y1="9" x2="27" y2="9" stroke="#60a5fa" strokeWidth="0.8" />
      <line x1="5" y1="23" x2="27" y2="23" stroke="#60a5fa" strokeWidth="0.8" />
    </svg>
  );
}

// 3D Cargo / Ship Graphic for Trade
export function ShipGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#1d4ed8" />
        </linearGradient>
        <linearGradient id="hullGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#082f49" />
        </linearGradient>
      </defs>
      <rect x="14" y="22" width="12" height="12" rx="2" fill="#f59e0b" />
      <rect x="28" y="20" width="14" height="14" rx="2" fill="url(#shipGrad)" />
      <rect x="44" y="24" width="10" height="10" rx="2" fill="#10b981" />
      <path d="M6 38 L58 38 L50 52 L14 52 Z" fill="url(#hullGrad)" stroke="#38bdf8" strokeWidth="1" />
      <path d="M2 50 C 14 46, 22 56, 34 50 C 46 44, 54 54, 62 50" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// 3D Growth / Export Graphic
export function ExportGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="expGrad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>
      </defs>
      <rect x="10" y="34" width="10" height="20" rx="2" fill="#0284c7" opacity="0.8" />
      <rect x="24" y="24" width="10" height="30" rx="2" fill="#0ea5e9" opacity="0.9" />
      <rect x="38" y="14" width="10" height="40" rx="2" fill="url(#expGrad)" />
      <path d="M12 28 L28 18 L44 8 L54 14" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <polygon points="54,8 54,16 46,14" fill="#34d399" />
    </svg>
  );
}

// 3D Truck / GST Logistics Graphic
export function TruckGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="truckGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#b45309" />
        </linearGradient>
      </defs>
      <rect x="8" y="20" width="30" height="22" rx="3" fill="url(#truckGrad)" stroke="#fde047" strokeWidth="1" />
      <path d="M38 28 L48 28 L54 35 L54 42 L38 42 Z" fill="#0284c7" />
      <rect x="40" y="30" width="8" height="6" rx="1" fill="#bae6fd" />
      <circle cx="18" cy="45" r="5" fill="#0f172a" stroke="#94a3b8" strokeWidth="2" />
      <circle cx="46" cy="45" r="5" fill="#0f172a" stroke="#94a3b8" strokeWidth="2" />
    </svg>
  );
}

// 3D Tax Receipts / Store Graphic
export function ReceiptGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="receiptGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#0369a1" />
        </linearGradient>
      </defs>
      <rect x="14" y="12" width="28" height="38" rx="4" fill="url(#receiptGrad)" stroke="#7dd3fc" strokeWidth="1" />
      <line x1="20" y1="20" x2="36" y2="20" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
      <line x1="20" y1="26" x2="32" y2="26" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
      <line x1="20" y1="32" x2="36" y2="32" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="38" cy="42" r="10" fill="#f59e0b" stroke="#fef08a" strokeWidth="1.5" />
      <text x="35" y="46" fill="#78350f" fontSize="12" fontWeight="bold">₹</text>
    </svg>
  );
}

// 3D Coins & Inflation Graphic
export function CoinsGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <ellipse cx="28" cy="42" rx="16" ry="6" fill="#b45309" />
      <ellipse cx="28" cy="38" rx="16" ry="6" fill="#f59e0b" stroke="#fef08a" strokeWidth="1" />
      <ellipse cx="28" cy="30" rx="16" ry="6" fill="#f59e0b" stroke="#fef08a" strokeWidth="1" />
      <ellipse cx="28" cy="22" rx="16" ry="6" fill="#fbbf24" stroke="#fef08a" strokeWidth="1.5" />
      <text x="25" y="25" fill="#78350f" fontSize="10" fontWeight="bold">%</text>
      <path d="M38 18 L48 8 L54 14" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
      <polygon points="54,8 54,16 46,14" fill="#ef4444" />
    </svg>
  );
}

// 3D RBI / Bank Building Graphic
export function BankGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="bankGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#78350f" />
        </linearGradient>
      </defs>
      <polygon points="32,10 10,24 54,24" fill="#38bdf8" stroke="#bae6fd" strokeWidth="1" />
      <rect x="14" y="24" width="36" height="4" fill="#0284c7" />
      <rect x="16" y="28" width="6" height="20" fill="url(#bankGrad)" rx="1" />
      <rect x="26" y="28" width="6" height="20" fill="url(#bankGrad)" rx="1" />
      <rect x="36" y="28" width="6" height="20" fill="url(#bankGrad)" rx="1" />
      <rect x="46" y="28" width="6" height="20" fill="url(#bankGrad)" rx="1" />
      <rect x="10" y="48" width="44" height="6" fill="#0284c7" rx="1" />
      <circle cx="32" cy="18" r="3" fill="#fbbf24" />
    </svg>
  );
}

// 3D Capital Expenditure Graphic
export function CapitalGraphic({ size = 42 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id="capGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0ea5e9" />
          <stop offset="100%" stopColor="#0369a1" />
        </linearGradient>
      </defs>
      <rect x="8" y="32" width="12" height="22" rx="2" fill="url(#capGrad)" />
      <rect x="24" y="20" width="12" height="34" rx="2" fill="#f59e0b" />
      <rect x="40" y="10" width="12" height="44" rx="2" fill="#10b981" />
      <path d="M12 24 L28 12 L44 4 L56 10" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
