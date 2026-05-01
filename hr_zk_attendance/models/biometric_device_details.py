# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Bhagyadev KP (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
# import datetime
import logging

import pytz
from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()  # e.g., "2025-07-15T17:10:30"
    raise TypeError(f"Type {type(obj)} not serializable")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""

    _name = "biometric.device.details"
    _description = "Biometric Device Details"

    name = fields.Char(
        string="Name",
        required=True,
        help="Record Name",
    )
    connection_mode = fields.Selection(
        selection=[
            ("zk", "ZK TCP Device"),
            ("web_api", "Web API (GetDeviceLogs)"),
        ],
        string="Integration",
        required=True,
        default="zk",
        help="Connect directly to the ZKTeco-style device via TCP/IP, "
        "or pull logs from an HTTP endpoint such as "
        ".../api/v2/WebAPI/GetDeviceLogs.",
    )
    web_api_base_url = fields.Char(
        string="Web API base URL",
        help='Host (and optional port), e.g. http://122.166.44.18:85 — '
        "paths /api/v2/WebAPI/GetDeviceLogs are appended automatically.",
    )
    web_api_key = fields.Char(
        string="Web API key",
        help="Value for the APIKey query parameter.",
    )
    web_api_days_back = fields.Integer(
        string="Auto-sync lookback (days)",
        default=1,
        help="Scheduled / “Sync now”: FromDate = today minus this many "
        "calendar days, ToDate = today (inclusive).",
    )
    web_api_serial_filter = fields.Char(
        string="Restrict to device serial",
        help="Optional SerialNumber from the API JSON. When set, punch rows "
        "from other readers are ignored.",
    )
    web_api_ignored_employee_codes = fields.Text(
        string="Ignored EmployeeCode list",
        help="Optional — one code per line or comma-separated. Rows whose "
        "EmployeeCode matches exactly (e.g. test cards 8888, 99999) are skipped.",
    )
    attendance_tz = fields.Char(
        string="Attendance timezone",
        help="IANA name for naive timestamps from the device or API "
        "(e.g. Asia/Kolkata). If empty, the scheduler user TZ or UTC "
        "is used.",
    )
    device_ip = fields.Char(
        string="Device IP",
        help="The IP address of the Device",
    )
    port_number = fields.Integer(
        string="Port Number",
        default=4370,
        help="The Port Number of the Device",
    )
    address_id = fields.Many2one(
        "res.partner",
        string="Working Address",
        help="Working address of the partner",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
        help="Current Company",
    )
    attendance_data = fields.Text(
        string="Last sync preview",
        readonly=True,
        help="JSON preview of the latest consolidated employee-days after sync.",
    )
    last_sync_at = fields.Datetime(
        string="Last sync",
        readonly=True,
        help="UTC time when Odoo last pulled from the Web API on this record.",
    )
    last_sync_period = fields.Char(string="Last synced period", readonly=True)
    last_sync_device_log_count = fields.Integer(
        string="Rows in last payload",
        readonly=True,
        help="Number of punch rows returned by GetDeviceLogs in the last run.",
    )
    last_sync_daily_rows = fields.Integer(
        string="Consolidated days (last run)",
        readonly=True,
        help="Employee calendar days written/updated in the last run.",
    )

    @api.constrains(
        "connection_mode",
        "device_ip",
        "port_number",
        "web_api_base_url",
        "web_api_key",
        "web_api_days_back",
    )
    def _check_connection_mode_params(self):
        for device in self:
            if device.connection_mode == "zk":
                if not device.device_ip or not device.port_number:
                    raise ValidationError(
                        _("ZK mode requires Device IP and Port Number.")
                    )
            else:
                if not device.web_api_base_url or not device.web_api_key:
                    raise ValidationError(
                        _("Web API mode requires Base URL and API key.")
                    )
                if device.web_api_days_back is not None and device.web_api_days_back < 0:
                    raise ValidationError(
                        _("Web API days to fetch cannot be negative.")
                    )

    def _attendance_tz_name(self):
        self.ensure_one()
        return self.attendance_tz or self.env.user.tz or "UTC"

    def _attendance_tz_pytz(self):
        self.ensure_one()
        try:
            return pytz.timezone(self._attendance_tz_name())
        except pytz.exceptions.UnknownTimeZoneError as err:
            raise UserError(_("Unknown attendance timezone %s") % self._attendance_tz_name()) from err

    def _find_employee_by_biometric_code(self, biometric_code):
        """Resolve employee: API EmployeeCode equals hr.employee.identification_id."""
        self.ensure_one()
        code = (biometric_code or "").strip()
        if not code:
            return self.env["hr.employee"].sudo().browse()

        Employee = self.env["hr.employee"].sudo()

        emp = Employee.search(
            [
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
                ("identification_id", "=", code),
            ],
            limit=1,
        )
        if emp:
            return emp

        return Employee.search(
            [
                ("company_id", "=", False),
                ("active", "=", True),
                ("identification_id", "=", code),
            ],
            limit=1,
        )

    def _apply_aggregated_to_hr_attendance(self, aggregated_records):
        """Create or update hr.attendance using min check-in / max check-out pairs."""
        self.ensure_one()
        hr_attendance = self.env["hr.attendance"].sudo()
        user_tz = self._attendance_tz_pytz()
        _logger.debug(
            "apply_aggregated_to_hr_attendance: TZ=%s, %s pairs",
            self._attendance_tz_name(),
            len(aggregated_records),
        )
        for record in aggregated_records:
            check_in_time_dt = record["check_in"]
            check_out_time_dt = record["check_out"]
            if check_in_time_dt.tzinfo is not None:
                check_in_time_dt = check_in_time_dt.astimezone(user_tz).replace(
                    tzinfo=None
                )
            if check_out_time_dt.tzinfo is not None:
                check_out_time_dt = check_out_time_dt.astimezone(user_tz).replace(
                    tzinfo=None
                )

            local_dt_in = user_tz.localize(check_in_time_dt, is_dst=None)
            utc_dt_in = local_dt_in.astimezone(pytz.utc)
            check_in_time = fields.Datetime.to_string(utc_dt_in)

            local_dt_out = user_tz.localize(check_out_time_dt, is_dst=None)
            utc_dt_out = local_dt_out.astimezone(pytz.utc)
            check_out_time = fields.Datetime.to_string(utc_dt_out)

            if check_in_time == check_out_time:
                check_out_time = utc_dt_out.strftime("%Y-%m-%d 14:00:00")

            cleaned_user_id = record["user_id"]
            if not cleaned_user_id:
                continue

            employee = self._find_employee_by_biometric_code(cleaned_user_id)
            if not employee:
                _logger.warning(
                    "No employee with Identification No matching %s in company %s",
                    cleaned_user_id,
                    self.company_id.name,
                )
                continue
            try:
                check_in_date = utc_dt_in.date()
                day_start_naive = datetime.combine(check_in_date, datetime.min.time())
                day_end_naive = datetime.combine(check_in_date, datetime.max.time())
                utc_day_start = pytz.utc.localize(day_start_naive)
                utc_day_end = pytz.utc.localize(day_end_naive)
                existing_attendance = hr_attendance.search(
                    [
                        ("employee_id", "=", employee.id),
                        ("check_in", ">=", fields.Datetime.to_string(utc_day_start)),
                        ("check_in", "<=", fields.Datetime.to_string(utc_day_end)),
                    ],
                    limit=1,
                )
                if existing_attendance:
                    existing_attendance.write(
                        {
                            "check_in": check_in_time,
                            "check_out": check_out_time,
                        }
                    )
                else:
                    hr_attendance.create(
                        {
                            "employee_id": employee.id,
                            "check_in": check_in_time,
                            "check_out": check_out_time,
                        }
                    )
            except Exception:
                _logger.exception(
                    "HR attendance sync failed employee=%s (%s)",
                    employee.name,
                    cleaned_user_id,
                )

    def _parse_web_api_log_datetime(self, log_date_str):
        if not log_date_str:
            return None
        if isinstance(log_date_str, datetime):
            return (
                log_date_str.replace(tzinfo=None)
                if log_date_str.tzinfo
                else log_date_str
            )
        if isinstance(log_date_str, date) and not isinstance(log_date_str, datetime):
            return datetime.combine(log_date_str, datetime.min.time())
        log_date_str = str(log_date_str).strip()
        log_date_str_norm = log_date_str.replace("T", " ")
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(log_date_str_norm, fmt)
            except ValueError:
                continue
        return None

    def _web_api_ignored_employee_codes_set(self):
        """Parse Text field as comma or newline separated exact EmployeeCode skips."""
        self.ensure_one()
        raw = (self.web_api_ignored_employee_codes or "").replace(",", "\n")
        return {x.strip() for x in raw.splitlines() if x.strip()}

    @staticmethod
    def _api_coerce_employee_code(value):
        """GetDeviceLogs EmployeeCode — must match hr.employee.identification_id."""
        if value is None or value is False:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                s = str(value).strip()
                return s or None
        if isinstance(value, int):
            return str(value)
        s = str(value).strip()
        return s or None

    @staticmethod
    def _api_row_serial_number(row):
        return str(
            row.get("SerialNumber") or row.get("serialNumber") or ""
        ).strip()

    def _api_normalize_punch_direction(self, raw):
        """
        GetDeviceLogs PunchDirection: blank = undirected punch; 'in' / 'out'.
        """
        if raw is None:
            return "neutral"
        if isinstance(raw, (int, float)):
            return "neutral"
        s = str(raw).strip().lower()
        if not s:
            return "neutral"
        if s in ("in", "i", "checkin", "check-in", "check_in", "cin"):
            return "in"
        if s in ("out", "o", "checkout", "check-out", "check_out", "cout"):
            return "out"
        return "neutral"

    def _api_row_log_datetime(self, row):
        return self._parse_web_api_log_datetime(
            row.get("LogDate") or row.get("logDate")
        )

    def _fetch_web_api_device_logs(self, from_dt, to_dt):
        """GET GetDeviceLogs and return decoded JSON rows (list)."""
        self.ensure_one()
        base = (self.web_api_base_url or "").strip().rstrip("/")
        if not base:
            raise UserError(_("Web API base URL is missing."))
        qs = urllib.parse.urlencode(
            {
                "APIKey": (self.web_api_key or "").strip(),
                "FromDate": from_dt.strftime("%Y-%m-%d"),
                "ToDate": to_dt.strftime("%Y-%m-%d"),
            }
        )
        path = "/api/v2/WebAPI/GetDeviceLogs"
        url = f"{base}{path}?{qs}"
        _logger.info("Fetching biometric logs GET %s", url.split("?", 1)[0])
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                body = resp.read().decode()
        except urllib.error.HTTPError as e:
            raise UserError(_("Web API HTTP error (%s): %s") % (e.code, e.reason)) from e
        except urllib.error.URLError as e:
            raise UserError(_("Web API unreachable: %s") % e.reason) from e
        body = body.lstrip("\ufeff").strip()
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as e:
            raise UserError(_("Web API returned non-JSON: %s") % e) from e
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            rows = (
                parsed.get("data")
                or parsed.get("Data")
                or parsed.get("logs")
                or parsed.get("records")
            )
            if isinstance(rows, list):
                return rows
        raise UserError(_("Unexpected Web API response shape; expected JSON list."))

    def aggregate_web_api_logs_first_in_last_out(self, log_rows):
        """
        Consume GetDeviceLogs rows shaped like:
          EmployeeCode, LogDate, SerialNumber, PunchDirection, Temperature,
          TemperatureState (camelCase variants are also accepted).

        First punch-in per (employee code, day): earliest PunchDirection 'in',
        else earliest time. Last punch-out: latest 'out'; if none, latest punch.
        """
        self.ensure_one()
        serial_required = (self.web_api_serial_filter or "").strip()
        skipped_codes = self._web_api_ignored_employee_codes_set()
        day_buckets = defaultdict(
            lambda: {
                "in_times": [],
                "out_times": [],
                "neutral_times": [],
            }
        )

        for row in log_rows:
            if not isinstance(row, dict):
                continue
            if serial_required:
                if self._api_row_serial_number(row) != serial_required:
                    continue

            emp_code = self._api_coerce_employee_code(
                row.get("EmployeeCode") or row.get("employeeCode")
            )
            if not emp_code:
                continue

            if emp_code in skipped_codes:
                continue

            ts = self._api_row_log_datetime(row)
            if not ts:
                continue
            bucket_key = (emp_code, ts.date())
            direction_raw = row.get("PunchDirection")
            if direction_raw is None:
                direction_raw = row.get("punchDirection")
            direction = self._api_normalize_punch_direction(direction_raw)
            bucket = day_buckets[bucket_key]
            if direction == "in":
                bucket["in_times"].append(ts)
            elif direction == "out":
                bucket["out_times"].append(ts)
            else:
                bucket["neutral_times"].append(ts)

        aggregated_records = []

        def pick_check_in(times_in, neutrals, outs):
            if times_in:
                return min(times_in)
            earliest = neutrals + outs
            return min(earliest) if earliest else None

        def pick_check_out(times_out, neutrals, ins_):
            if times_out:
                return max(times_out)
            merged = neutrals + ins_
            return max(merged) if merged else None

        for (user_id, day_key), b in sorted(day_buckets.items()):
            tins = sorted(b["in_times"])
            touts = sorted(b["out_times"])
            tneut = sorted(b["neutral_times"])
            check_in = pick_check_in(tins, tneut, touts)
            check_out = pick_check_out(touts, tneut, tins)

            if not check_in:
                continue
            if check_out is None:
                check_out = check_in
            if check_out < check_in:
                check_out = check_in

            aggregated_records.append(
                {
                    "user_id": user_id,
                    "date": day_key,
                    "check_in": check_in.replace(tzinfo=None),
                    "check_out": check_out.replace(tzinfo=None),
                    "original_record": {},
                }
            )

        _logger.info(
            "aggregate_web_api: %s API rows → %s day rows",
            len(log_rows),
            len(aggregated_records),
        )
        return aggregated_records

    def _sync_web_api_date_range(self, from_date, to_date):
        """Pull GetDeviceLogs for [from_date, to_date], consolidate, write hr.attendance."""
        self.ensure_one()
        if self.connection_mode != "web_api":
            raise UserError(_("This device is not configured for Web API sync."))
        log_rows = self._fetch_web_api_device_logs(from_date, to_date)
        aggregated = self.aggregate_web_api_logs_first_in_last_out(log_rows)
        preview = [
            {
                "user_id": r["user_id"],
                "employee_code": r["user_id"],
                "work_date": str(r["date"]),
                "check_in": r["check_in"].isoformat(),
                "check_out": r["check_out"].isoformat(),
            }
            for r in aggregated
        ]
        period = _("%(f)s → %(t)s") % {
            "f": fields.Date.to_string(from_date),
            "t": fields.Date.to_string(to_date),
        }
        self.write(
            {
                "attendance_data": json.dumps(preview, indent=2),
                "last_sync_at": fields.Datetime.now(),
                "last_sync_period": period,
                "last_sync_device_log_count": len(log_rows),
                "last_sync_daily_rows": len(aggregated),
            }
        )
        self._apply_aggregated_to_hr_attendance(aggregated)
        return {"raw_logs": len(log_rows), "daily_rows": len(aggregated)}

    def _web_api_download_attendance(self):
        self.ensure_one()
        days_back = max(0, int(self.web_api_days_back or 0))
        to_date = fields.Date.today()
        from_date = to_date - relativedelta(days=days_back)
        return self._sync_web_api_date_range(from_date, to_date)

    def action_open_fetch_by_date_wizard(self):
        self.ensure_one()
        if self.connection_mode != "web_api":
            raise UserError(
                _("Open this wizard only for devices using Web API integration.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Fetch by date"),
            "res_model": "biometric.attendance.fetch.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_device_id": self.id},
        }

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        _logger.debug(f"device_connect: Attempting to connect to device {self.device_ip}:{self.port_number}")

        try:
            conn = zk.connect()
            if conn:
                _logger.info(f"device_connect: Successfully connected to device {self.device_ip}:{self.port_number}")
                return conn
            else:
                _logger.error(f"device_connect: Failed to connect to device {self.device_ip}:{self.port_number}")
                return False
        except Exception as e:
            _logger.error(
                f"device_connect: Exception while connecting to device {self.device_ip}:{self.port_number}: {str(e)}")
            return False

    def action_test_connection(self):
        """Ping ZK over TCP or call the Web API with today's date."""
        self.ensure_one()
        if self.connection_mode == "web_api":
            try:
                today = fields.Date.today()
                self._fetch_web_api_device_logs(today, today)
            except UserError:
                raise
            except Exception as error:
                raise ValidationError(_("Web API failed: %s") % error) from error
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("Web API reachable (parsed JSON logs)."),
                    "type": "success",
                    "sticky": False,
                },
            }
        zk = ZK(
            self.device_ip,
            port=self.port_number,
            timeout=30,
            password=False,
            ommit_ping=False,
        )
        try:
            connect = zk.connect()
            if connect:
                connect.disconnect()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": _("Successfully connected to the biometric device."),
                        "type": "success",
                        "sticky": False,
                    },
                }
            raise ValidationError(_("Could not reach the biometric device."))
        except Exception as error:
            raise ValidationError(f"{error}") from error

    def action_set_timezone(self, existing_conn=None):
        """Function to set user's timezone to device"""
        for info in self:
            if info.connection_mode == "web_api":
                raise UserError(_("Set Time applies only to ZK TCP devices."))
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # If no existing connection, create one
                if not existing_conn:
                    zk = ZK(
                        machine_ip,
                        port=zk_port,
                        timeout=15,
                        password=0,
                        force_udp=False,
                        ommit_ping=False,
                    )
                    conn = self.device_connect(zk)
                else:
                    conn = existing_conn
            except NameError:
                raise UserError(
                    _(
                        "Pyzk module not Found. Please install it with 'pip3 install pyzk'."
                    )
                )
            if conn:
                user_tz = self.env.context.get("tz") or self.env.user.tz or "UTC"
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz)
                )
                conn.set_time(user_timezone_time)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": "Successfully Set the Time",
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise UserError(_("Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            if info.connection_mode == "web_api":
                raise UserError(
                    _(
                        "Clear on device applies only to ZK TCP integrations. "
                        "Disable or purge attendance in Odoo if needed."
                    )
                )
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(
                        machine_ip,
                        port=zk_port,
                        timeout=30,
                        password=0,
                        force_udp=False,
                        ommit_ping=False,
                    )
                except NameError:
                    raise UserError(_("Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        # conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute("""delete from zk_machine_attendance""")
                        # conn.disconnect()
                    else:
                        raise UserError(
                            _(
                                "Unable to clear Attendance log.Are you sure "
                                "attendance log is not empty."
                            )
                        )
                else:
                    raise UserError(
                        _(
                            "Unable to connect to Attendance Device. Please use "
                            "Test Connection button to verify."
                        )
                    )
            except Exception as error:
                raise ValidationError(f"{error}")

    @api.model
    def cron_download(self):
        machines = self.env["biometric.device.details"].search([])
        for machine in machines:
            machine.with_company(machine.company_id).action_download_attendance()

    def convert_biometric_timestamp(self, timestamp_bytes):
        """Convert biometric device timestamp bytes to datetime"""
        _logger.debug(f"convert_biometric_timestamp: Input type: {type(timestamp_bytes)}")
        _logger.debug(f"convert_biometric_timestamp: Input value: {repr(timestamp_bytes)}")

        try:
            # If timestamp is already a datetime object, return it
            if isinstance(timestamp_bytes, datetime):
                _logger.debug(f"convert_biometric_timestamp: Input is already datetime: {timestamp_bytes}")
                return timestamp_bytes

            # If timestamp is a date object, convert to datetime
            if isinstance(timestamp_bytes, date):
                _logger.debug(f"convert_biometric_timestamp: Input is date, converting to datetime: {timestamp_bytes}")
                return datetime.combine(timestamp_bytes, datetime.min.time())

            # If timestamp is a string, try to parse it
            if isinstance(timestamp_bytes, str):
                _logger.debug(f"convert_biometric_timestamp: Input is string: {timestamp_bytes}")
                try:
                    # Try common datetime formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                        try:
                            dt = datetime.strptime(timestamp_bytes, fmt)
                            _logger.debug(f"convert_biometric_timestamp: Parsed string with format {fmt}: {dt}")
                            return dt
                        except ValueError:
                            continue
                    _logger.warning(f"convert_biometric_timestamp: Could not parse string timestamp: {timestamp_bytes}")
                    return None
                except Exception as e:
                    _logger.error(f"convert_biometric_timestamp: Error parsing string timestamp: {str(e)}")
                    return None

            # If timestamp is bytes, process as before
            if isinstance(timestamp_bytes, bytes):
                _logger.debug(f"convert_biometric_timestamp: Input is bytes, length: {len(timestamp_bytes)}")

                if not timestamp_bytes or timestamp_bytes == b'\x00\x00\x00\x00':
                    _logger.warning("convert_biometric_timestamp: Invalid timestamp (null or empty bytes)")
                    return None

                # Convert bytes to integer timestamp
                timestamp_int = int.from_bytes(timestamp_bytes, byteorder='little')
                _logger.debug(f"convert_biometric_timestamp: Converted bytes to integer: {timestamp_int}")

                # Convert to datetime (assuming Unix timestamp)
                dt = datetime.fromtimestamp(timestamp_int)
                _logger.debug(f"convert_biometric_timestamp: Converted integer to datetime: {dt}")

                return dt

            # If timestamp is an integer, convert directly
            if isinstance(timestamp_bytes, int):
                _logger.debug(f"convert_biometric_timestamp: Input is integer: {timestamp_bytes}")
                dt = datetime.fromtimestamp(timestamp_bytes)
                _logger.debug(f"convert_biometric_timestamp: Converted integer to datetime: {dt}")
                return dt

            # If timestamp is a float, convert directly
            if isinstance(timestamp_bytes, float):
                _logger.debug(f"convert_biometric_timestamp: Input is float: {timestamp_bytes}")
                dt = datetime.fromtimestamp(timestamp_bytes)
                _logger.debug(f"convert_biometric_timestamp: Converted float to datetime: {dt}")
                return dt

            _logger.warning(f"convert_biometric_timestamp: Unsupported timestamp type: {type(timestamp_bytes)}")
            return None

        except Exception as e:
            _logger.error(
                f"convert_biometric_timestamp: Error converting timestamp {repr(timestamp_bytes)} of type {type(timestamp_bytes)}: {str(e)}")
            return None

    def roundtrip_time_conversion(self, original_dt_str, user):
        """Demonstrates full conversion cycle"""
        user_tz = user.tz or 'UTC'

        # 1. Original is in user's local time
        original_dt = datetime.strptime(original_dt_str, "%Y-%m-%d %H:%M:%S")
        local_dt = pytz.timezone(user_tz).localize(original_dt, is_dst=None)

        # 2. Convert to UTC for storage
        utc_dt = local_dt.astimezone(pytz.utc)
        utc_str = utc_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 3. Convert back to user's timezone for display
        stored_utc_dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
        stored_utc_dt = pytz.utc.localize(stored_utc_dt)
        display_dt = stored_utc_dt.astimezone(pytz.timezone(user_tz))

        return {
            'original': original_dt_str,
            'utc': utc_str,
            'display': fields.Datetime.to_string(display_dt)
        }

    def action_download_attendance(self):
        """Pull attendance via Web API or from the device over TCP."""

        try:
            if self.connection_mode == "web_api":
                _logger.info(
                    "action_download_attendance: Web API sync for %s (company=%s)",
                    self.name,
                    self.company_id.name,
                )
                stats = self._web_api_download_attendance()
                _logger.info(
                    "action_download_attendance: Web API attendance sync completed"
                )
                msg = _(
                    "%(raw)s punch rows pulled; %(day)s employee-day attendances "
                    "updated in Odoo (lookback: %(lookback)s day(s))."
                ) % {
                    "raw": stats["raw_logs"],
                    "day": stats["daily_rows"],
                    "lookback": self.web_api_days_back,
                }
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": msg,
                        "type": "success",
                        "sticky": False,
                    },
                }

        except Exception as e:
            _logger.exception("action_download_attendance: Web API error: %s", e)
            raise

        _logger.info(
            "action_download_attendance: ZK TCP download %s (%s:%s)",
            self.name,
            self.device_ip,
            self.port_number,
        )

        try:
            zk = ZK(
                self.device_ip,
                port=self.port_number,
                timeout=15,
                password=0,
                force_udp=False,
                ommit_ping=False,
            )
            _logger.debug("action_download_attendance: ZK object created successfully")

            conn = self.device_connect(zk)
            if not conn:
                _logger.error("action_download_attendance: Failed to connect to device")
                raise UserError(_("Unable to connect, please check the parameters and network connections."))

            _logger.info("action_download_attendance: Successfully connected to device")

            self.action_set_timezone(conn)
            _logger.debug("action_download_attendance: Timezone set successfully using existing connection")

            if conn:
                try:
                    _logger.debug("action_download_attendance: Disabling device for data retrieval")
                    conn.disable_device()  # Device Cannot be used during this time.

                    _logger.debug("action_download_attendance: Getting users from device")
                    users = conn.get_users()
                    _logger.info(f"action_download_attendance: Found {len(users) if users else 0} users on device")

                    _logger.debug("action_download_attendance: Getting attendance data from device")
                    attendance = conn.get_attendance()
                    _logger.info(
                        f"action_download_attendance: Found {len(attendance) if attendance else 0} attendance records on device")

                    if attendance:
                        _logger.info("action_download_attendance: Processing attendance data")

                        # Process and clean attendance data
                        valid_attendance = self.process_attendance_data(attendance)
                        _logger.info(
                            f"action_download_attendance: {len(valid_attendance)} valid records after processing")

                        # Aggregate attendance data by user and date (min/max all punches).
                        aggregated_attendance = (
                            self.aggregate_attendance_by_user_date(valid_attendance)
                        )
                        _logger.info(
                            f"action_download_attendance: {len(aggregated_attendance)} aggregated records after aggregation"
                        )

                        self._apply_aggregated_to_hr_attendance(aggregated_attendance)
                        self.attendance_data = json.dumps(aggregated_attendance, default=str)
                        _logger.info("action_download_attendance: Attendance download completed successfully")
                        return True
                    else:
                        _logger.warning("action_download_attendance: No attendance data found on device")
                        raise UserError(_("Unable to get the attendance log, please try again later."))

                except Exception as e:
                    _logger.error(f"action_download_attendance: Error during data processing: {str(e)}")
                    raise
                finally:
                    _logger.debug("action_download_attendance: Disconnecting from device")
                    conn.disconnect()
            else:
                _logger.error("action_download_attendance: Connection object is None")
                raise UserError(_("Unable to connect, please check the parameters and network connections."))

        except Exception as e:
            _logger.error(f"action_download_attendance: Unexpected error: {str(e)}")
            raise

    def action_restart_device(self):
        """For restarting the device"""
        self.ensure_one()
        if self.connection_mode == "web_api":
            raise UserError(_("Restart is only available for ZK TCP devices."))
        zk = ZK(
            self.device_ip,
            port=self.port_number,
            timeout=15,
            password=0,
            force_udp=False,
            ommit_ping=False,
        )
        self.device_connect(zk).restart()

    def clean_user_id(self, user_id):
        """
        Clean and extract valid user_id from corrupted biometric device data
        Handles various encoding issues and hex escape sequences
        """
        if not user_id:
            _logger.debug("clean_user_id: Input user_id is None or empty")
            return None

        try:
            _logger.debug(f"clean_user_id: Processing user_id: {repr(user_id)}")

            # Convert to string if it's bytes
            if isinstance(user_id, bytes):
                user_id_str = user_id.decode('utf-8', errors='ignore')
                _logger.debug(f"clean_user_id: Converted bytes to string: {repr(user_id_str)}")
            else:
                user_id_str = str(user_id)
                _logger.debug(f"clean_user_id: Input is already string: {repr(user_id_str)}")

            # Remove common hex escape sequences and control characters
            import re

            # Remove hex escape sequences like \x04, \x0f, \x01, etc.
            user_id_str = re.sub(r'\\x[0-9a-fA-F]{2}', '', user_id_str)
            _logger.debug(f"clean_user_id: After removing hex sequences: {repr(user_id_str)}")

            # Remove other control characters
            user_id_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_id_str)
            _logger.debug(f"clean_user_id: After removing control chars: {repr(user_id_str)}")

            # Remove non-printable characters
            user_id_str = ''.join(char for char in user_id_str if char.isprintable())
            _logger.debug(f"clean_user_id: After removing non-printable: {repr(user_id_str)}")

            # Strip whitespace
            user_id_str = user_id_str.strip()
            _logger.debug(f"clean_user_id: After stripping whitespace: {repr(user_id_str)}")

            # If empty after cleaning, return None
            if not user_id_str:
                _logger.debug("clean_user_id: Result is empty after cleaning")
                return None

            # Try to extract numeric user ID
            # Look for numeric patterns in the cleaned string
            numeric_match = re.search(r'\d+', user_id_str)
            if numeric_match:
                result = numeric_match.group()
                _logger.debug(f"clean_user_id: Extracted numeric ID: {result}")
                return result

            # If no numeric pattern found, return the cleaned string if it looks valid
            if user_id_str.isalnum() and len(user_id_str) <= 10:
                _logger.debug(f"clean_user_id: Using alphanumeric result: {user_id_str}")
                return user_id_str

            _logger.debug(f"clean_user_id: No valid user_id found in: {repr(user_id_str)}")
            return None

        except Exception as e:
            _logger.error(f"clean_user_id: Error cleaning user_id {repr(user_id)}: {str(e)}")
            return None

    def aggregate_attendance_by_user_date(self, valid_attendance):
        """
        Aggregate attendance records by user and date
        Uses minimum time as check-in and maximum time as check-out
        """
        _logger.info(f"aggregate_attendance_by_user_date: Aggregating {len(valid_attendance)} attendance records")
        
        # Group records by user_id and date
        attendance_groups = {}
        
        for record in valid_attendance:
            try:
                user_id = record['user_id']
                if not user_id:
                    continue
                
                # Parse timestamp to get date
                if isinstance(record['timestamp'], str):
                    timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                elif isinstance(record['timestamp'], datetime):
                    timestamp = record['timestamp']
                else:
                    _logger.warning(f"aggregate_attendance_by_user_date: Invalid timestamp format for record: {record}")
                    continue
                
                date_key = timestamp.date()
                group_key = (user_id, date_key)
                
                if group_key not in attendance_groups:
                    attendance_groups[group_key] = {
                        'user_id': user_id,
                        'date': date_key,
                        'timestamps': [],
                        'records': []
                    }
                
                attendance_groups[group_key]['timestamps'].append(timestamp)
                attendance_groups[group_key]['records'].append(record)
                
            except Exception as e:
                _logger.error(f"aggregate_attendance_by_user_date: Error processing record {record}: {str(e)}")
                continue
        
        # Create aggregated attendance records
        aggregated_records = []
        
        for group_key, group_data in attendance_groups.items():
            try:
                user_id = group_data['user_id']
                date_key = group_data['date']
                timestamps = group_data['timestamps']
                
                if not timestamps:
                    continue
                
                # Find min and max timestamps
                min_timestamp = min(timestamps)
                max_timestamp = max(timestamps)
                
                # Create aggregated record
                aggregated_record = {
                    'user_id': user_id,
                    'date': date_key,
                    'check_in': min_timestamp,
                    'check_out': max_timestamp,
                    'total_records': len(timestamps),
                    'all_timestamps': sorted(timestamps),
                    'original_records': group_data['records']
                }
                
                aggregated_records.append(aggregated_record)
                
                _logger.debug(f"aggregate_attendance_by_user_date: User {user_id} on {date_key}: "
                            f"check_in={min_timestamp}, check_out={max_timestamp}, "
                            f"total_punches={len(timestamps)}")
                
            except Exception as e:
                _logger.error(f"aggregate_attendance_by_user_date: Error aggregating group {group_key}: {str(e)}")
                continue
        
        _logger.info(f"aggregate_attendance_by_user_date: Created {len(aggregated_records)} aggregated records")
        return aggregated_records

    def process_attendance_data(self, attendance_records):
        """
        Process and clean attendance data, returning only valid records
        """
        _logger.info(f"process_attendance_data: Processing {len(attendance_records)} attendance records")
        valid_records = []
        
        for i, record in enumerate(attendance_records):
            _logger.debug(f"process_attendance_data: Processing record {i + 1}/{len(attendance_records)}")
            _logger.debug(
                f"process_attendance_data: Record {i + 1} attributes: {[attr for attr in dir(record) if not attr.startswith('_')]}")
            ts = self.convert_biometric_timestamp(record.timestamp)
            try:
                cleaned_user_id = self.clean_user_id(record.user_id)
                valid_record = {
                    'user_id': cleaned_user_id,
                    'original_user_id': record.user_id,
                    'timestamp': ts,
                    'original_timestamp': record.timestamp,
                    'punch': record.punch if hasattr(record, 'punch') else 0,
                    'status': record.status if hasattr(record, 'status') else 0,
                    'uid': record.uid if hasattr(record, 'uid') else 0
                }
                
                valid_records.append(valid_record)
                _logger.debug(f"process_attendance_data: Added valid record {i + 1}: {valid_record}")

            except Exception as e:
                _logger.error(f"process_attendance_data: Error processing record {i + 1}: {str(e)}")
                continue

        _logger.info(
            f"process_attendance_data: Successfully processed {len(valid_records)}/{len(attendance_records)} records")
        return valid_records
