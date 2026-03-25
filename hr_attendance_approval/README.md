# HR Attendance Approval Module

## Overview
This module provides a dynamic multi-level attendance approval system for Odoo 17.

## Features

### Daily Attendance
- Employees can check-in and check-out daily
- Attendance records track worked hours automatically
- Employees submit their attendance for manager approval

### Approval Workflow
- **Individual Approval**: Managers can approve/reject attendance one by one
- **Bulk Approval**: Approve multiple attendance records at once with filters
- **Multi-Level Approval**: Configure multiple approval levels (Manager → Department Head → HR)

### Access Control (Security Groups)
1. **User**: Can create and view own attendance records
2. **Manager**: Can view and approve direct reports' attendance
3. **Super Manager**: Can view all managers' and employees' attendance
4. **Administrator**: Full access - can create, edit, delete any record

### Configurable Approval Levels
Configure approval workflow with these approver types:
- Direct Manager
- Department Manager  
- Specific User
- User Group

## Installation
1. Copy the `hr_attendance_approval` folder to your addons path
2. Update the apps list in Odoo
3. Install the module "HR Attendance Approval"

## Configuration
1. Go to **Attendance Approval > Configuration > Approval Configuration**
2. Create or modify the approval configuration
3. Add approval levels with the desired sequence and approver type
4. Optionally, assign specific departments to the configuration

## Usage

### For Employees
1. Go to **Attendance Approval > Attendance > My Attendance**
2. Create a new attendance record for today
3. Click **Check In** when starting work
4. Click **Check Out** when ending work
5. Click **Submit for Approval** to send to manager

### For Managers
1. Go to **Attendance Approval > Approvals > To Approve**
2. Review pending attendance records
3. Click **Approve** or **Reject** for individual records
4. Use **Action > Bulk Approve Attendance** for multiple records

### For Administrators
- Full access to all attendance records
- Can edit, create, or delete any record
- Configure approval workflows

## Dependencies
- `base`
- `hr`
- `hr_attendance`

## Technical Details

### Models
- `hr.attendance.approval` - Main attendance record with approval workflow
- `hr.attendance.approval.config` - Approval configuration
- `hr.attendance.approval.level` - Approval level definition
- `hr.attendance.approval.line` - Approval history log

### Security Groups
- `group_attendance_approval_user`
- `group_attendance_approval_manager`
- `group_attendance_approval_super_manager`
- `group_attendance_approval_admin`

## License
LGPL-3
