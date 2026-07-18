const allNavigation = [
  { href: "/app/dashboard", label: "대시보드" },
  { href: "/app/requests", label: "고객 요청" },
  { href: "/app/quotes", label: "견적" },
  { href: "/app/pricing", label: "가격 검토" },
  { href: "/app/approvals", label: "승인" },
  { href: "/app/reports", label: "리포트" },
  { href: "/app/operations", label: "운영", roles: ["admin"] },
  { href: "/app/demo", label: "데모", roles: ["admin"], demoOnly: true }
];

export function navigationFor(role, { demoEnabled = false } = {}) {
  return allNavigation.filter((item) => {
    if (item.demoOnly && !demoEnabled) return false;
    return !item.roles || item.roles.includes(role);
  });
}

export function roleLabel(role) {
  return { admin: "관리자", manager: "매니저", viewer: "뷰어" }[role] || "알 수 없는 역할";
}
