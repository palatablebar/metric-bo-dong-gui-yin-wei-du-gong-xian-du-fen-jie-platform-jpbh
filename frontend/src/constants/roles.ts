/** 角色 -> 权限点。后端唯一定义处：backend/src/constants/roles.py */
import type { Role } from '../types/models';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '分析负责人',
  analyst: '分析师',
  exec: '管理层（只读）',
};

export const PERMISSIONS: Record<Role, string[]> = {
  admin: [
    'metric:read',
    'metric:write',
    'dimension:read',
    'baseline:read',
    'attribution:run',
    'drilldown:read',
    'report:read',
    'report:write',
    'report:distribute',
    'export:read',
    'audit:read',
  ],
  analyst: [
    'metric:read',
    'dimension:read',
    'baseline:read',
    'attribution:run',
    'drilldown:read',
    'report:read',
    'report:write',
    'export:read',
  ],
  exec: ['metric:read', 'report:read'],
};

export function can(role: Role | undefined, permission: string): boolean {
  if (!role) return false;
  return PERMISSIONS[role].includes(permission);
}
