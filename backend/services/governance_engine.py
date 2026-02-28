from dataclasses import dataclass

from core.config import settings
from models.enums import UserRole
from models.user import User
from schemas.query import GovernanceDecision, SQLAnalysis


@dataclass(frozen=True)
class RoleRule:
    allowed_types: set[str]
    requires_approval_types: set[str]


ROLE_PERMISSIONS: dict[UserRole, RoleRule] = {
    UserRole.ADMIN: RoleRule({"SELECT", "INSERT", "UPDATE", "DELETE"}, set()),
    UserRole.DEVELOPER: RoleRule({"SELECT", "INSERT", "UPDATE", "DELETE"}, {"DELETE"}),
    UserRole.ANALYST: RoleRule({"SELECT", "INSERT", "UPDATE"}, {"INSERT", "UPDATE"}),
    UserRole.VIEWER: RoleRule({"SELECT"}, set()),
    UserRole.RESTRICTED: RoleRule({"SELECT"}, {"SELECT"}),
}


class GovernanceEngine:
    def decide(self, user: User, analysis: SQLAnalysis) -> GovernanceDecision:
        qtype = analysis.query_type.upper()
        if qtype in {"INVALID", "UNKNOWN"}:
            return GovernanceDecision(
                decision="DENIED",
                reason="Generated SQL is invalid or unsafe",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        if qtype in {"DROP", "TRUNCATE", "ALTER"}:
            return GovernanceDecision(
                decision="DENIED",
                reason="Destructive DDL is prohibited",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        if analysis.injection_patterns:
            return GovernanceDecision(
                decision="DENIED",
                reason="Potential injection pattern detected",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        if any(
            t.lower() in {x.lower() for x in settings.BLACKLISTED_TABLES}
            for t in analysis.tables_accessed
        ):
            return GovernanceDecision(
                decision="DENIED",
                reason="Blacklisted table access denied",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        allowed_tables = {t.lower() for t in user.allowed_tables}
        if allowed_tables and any(
            t.lower() not in allowed_tables for t in analysis.tables_accessed
        ):
            return GovernanceDecision(
                decision="DENIED",
                reason="Table is outside user allowed_tables",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        role_rule = ROLE_PERMISSIONS[user.role]
        if qtype not in role_rule.allowed_types:
            return GovernanceDecision(
                decision="DENIED",
                reason=f"Role {user.role.value} cannot execute {qtype}",
                risk_level=analysis.risk_level,
                mask_columns=[],
            )

        if user.role == UserRole.RESTRICTED:
            return GovernanceDecision(
                decision="REQUIRES_APPROVAL",
                reason="Restricted users require approval",
                risk_level=analysis.risk_level,
                mask_columns=settings.SENSITIVE_COLUMNS,
            )

        if qtype in role_rule.requires_approval_types:
            return GovernanceDecision(
                decision="REQUIRES_APPROVAL",
                reason=f"{qtype} requires human approval for this role",
                risk_level=analysis.risk_level,
                mask_columns=settings.SENSITIVE_COLUMNS,
            )

        if analysis.risk_level == "CRITICAL":
            return GovernanceDecision(
                decision="REQUIRES_APPROVAL",
                reason="Critical risk requires approval",
                risk_level=analysis.risk_level,
                mask_columns=settings.SENSITIVE_COLUMNS,
            )

        return GovernanceDecision(
            decision="APPROVED",
            reason="Governance checks passed",
            risk_level=analysis.risk_level,
            mask_columns=settings.SENSITIVE_COLUMNS,
        )
