# Countdown Task Integration Test Guide

This document provides step-by-step instructions for testing the countdown task manager across all three protocol paths: UDP, MQTT, and BLE.

## Quick Overview

The countdown task system supports three protocols:
- **UDP JSON**: Direct command endpoint on port 5569
- **MQTT**: Topic-based control via `iot/device/{MAC}/timer`
- **BLE**: Mesh vendor extension with 10-byte fragmented frames

All three paths converge to the same `app_countdown_add_task()` function, which manages task execution with 1-second precision.

---

## Prerequisites

- Device must be flashed with latest firmware build (after BLE countdown integration)
- Device must have network connectivity (WiFi for UDP/MQTT, BLE for BLE protocol)
- Test scripts: `tools/udp_countdown_test.py`, `tools/ble_countdown_test.py`
- Monitor device output: `idf.py monitor` or equivalent

---

## Test Case 1: UDP Protocol - One-Time Task

**Objective**: Verify UDP JSON command reaches countdown manager and executes at scheduled time.

### Setup
```bash
# In terminal 1: Monitor device output
cd /home/ats/standard_code/Aputure_IP_Project
source /home/ats/esp-idf/export.sh
idf.py monitor -p /dev/ttyUSB0
```

### Test Command
```bash
# In terminal 2: Send UDP command (task executes in 60 seconds)
cd /home/ats/standard_code/Aputure_IP_Project
python3 tools/udp_countdown_test.py add \
  --ip <DEVICE_IP> \
  --task-id 101 \
  --in-seconds 60 \
  --power on \
  --mode cct \
  --lightness 70 \
  --cct 5600
```

### Expected Behavior
1. Script outputs UDP JSON payload sent to device
2. Device monitor shows log: `[countdown] Task 101 added via UDP`
3. After 60 seconds: Device executes task (light turns on with specified color)
4. Monitor log: `[countdown] Task 101 matched time, executing state update`

### Verification
```bash
# Query task status before execution
python3 tools/udp_countdown_test.py query --ip <DEVICE_IP> --task-id 101

# List all tasks
python3 tools/udp_countdown_test.py list --ip <DEVICE_IP>

# Check task stats
python3 tools/udp_countdown_test.py stats --ip <DEVICE_IP>
```

---

## Test Case 2: UDP Protocol - Daily Recurring Task

**Objective**: Verify daily recurring task function.

### Test Command
```bash
# Schedule daily light turn-on at 22:00 (10 PM)
python3 tools/udp_countdown_test.py add \
  --ip <DEVICE_IP> \
  --task-id 102 \
  --type daily \
  --trigger-time "2026-04-21T22:00:00" \
  --power on \
  --mode cct \
  --lightness 80 \
  --cct 4000
```

### Expected Behavior
- Task persists across device reboots (stored in NVS flash)
- Every day at 22:00, device executes light on command
- Device monitors logs each execution with timestamp

---

## Test Case 3: BLE Protocol - One-Time Task

**Objective**: Verify BLE fragmentation and TLV parsing.

### Setup
```bash
# Generate BLE frames for task
python3 tools/ble_countdown_test.py once \
  --task-id 201 \
  --in-seconds 120 \
  --power on \
  --mode cct \
  --lightness 60 \
  --cct 6500 \
  --debug
```

This outputs hex frames:
```
Frame 0: BEGIN | 300100050000000065DF
Frame 1: CHUNK | 3101000500010707EA7B
Frame 2: CHUNK | 310101050015092F230B
...
Frame N: COMMIT | 32010005000000006517
```

### Sending via BLE
The above frames must be sent to the device via BLE mesh vendor extension. This requires:
1. a BLE client (e.g., mobile app, Python BLE library)
2. Ability to send 10-byte vendor extension packets
3. Session ID management (or use default session 1)

**Note**: Frame-by-frame BLE transmission is outside the scope of this tool (depends on device-side BLE mesh integration). The frames above can be:
- Logged and manually transmitted via a custom BLE app
- Integrated into automated test harness using `bleak` or similar Python BLE library

### Expected Device Side
When BLE frames arrive:
1. Device matches BEGIN session and allocates buffer
2. Receives CHUNK frames, accumulates TLV data
3. COMMIT triggers `app_ble_countdown_commit_cb()`
4. TLV parser extracts time + state → `countdown_task_t`
5. Task queued to `app_countdown_add_task()`
6. After 120s: Light turns on with specified color

### Example BLE Session Logs
```
[ble] Frame BEGIN received, session=1, type=ONCE, task_id=201
[ble] Frame CHUNK seq=0/5, session=1, task_id=201
[ble] Frame CHUNK seq=1/5, session=1, task_id=201
...
[ble] Frame COMMIT received, session=1, crc_check=OK
[countdown] BLE task 201 added via BLE mesh
[power] Task 201: setting state CCT mode, lightness=60, cct=6500
```

---

## Test Case 4: BLE Protocol - Daily Task

```bash
# Daily wake-up at 7:00 AM with HSI warm white
python3 tools/ble_countdown_test.py daily \
  --task-id 202 \
  --hour 7 \
  --minute 0 \
  --power on \
  --mode hsi \
  --hue 30 \
  --sat 100 \
  --lightness 70
```

Expected frames (5 total): BEGIN + 3 CHUNK + COMMIT

---

## Test Case 5: BLE Protocol - Weekly Task

```bash
# Every Monday at 8:00 AM, turn on with green hue
python3 tools/ble_countdown_test.py weekly \
  --task-id 203 \
  --weekday 1 \
  --hour 8 \
  --minute 0 \
  --power on \
  --mode hsi \
  --hue 120 \
  --sat 80 \
  --lightness 50
```

---

## Test Case 6: Verify Persistence - NVS Flash

**Objective**: Confirm task survives device reboot.

### Steps
1. Add three UDP tasks with different types:
   ```bash
   # Once task (6 hours from now)
   python3 tools/udp_countdown_test.py add --ip <DEVICE_IP> --task-id 301 \
     --trigger-time "2026-04-21T22:00:00" --power on --mode cct --cct 5000
   
   # Daily task (22:30 every day)
   python3 tools/udp_countdown_test.py add --ip <DEVICE_IP> --task-id 302 \
     --type daily --trigger-time "2026-04-21T22:30:00" --power off
   
   # Weekly task (Monday 10:00)
   python3 tools/udp_countdown_test.py add --ip <DEVICE_IP> --task-id 303 \
     --type weekly --trigger-time "2026-04-21T10:00:00" --power on
   ```

2. List tasks to confirm:
   ```bash
   python3 tools/udp_countdown_test.py list --ip <DEVICE_IP>
   ```

3. Reboot device (power off/on or `idf.py monitor` command)

4. Immediately query task list post-reboot:
   ```bash
   python3 tools/udp_countdown_test.py list --ip <DEVICE_IP>
   ```

### Expected Behavior
- All three tasks still present with correct parameters
- Task status remains intact (e.g., ONCE status changes to DONE after execution)

---

## Test Case 7: Task Cleanup

**Objective**: Verify remove and clear operations.

### Remove Single Task
```bash
python3 tools/udp_countdown_test.py remove --ip <DEVICE_IP> --task-id 101
python3 tools/udp_countdown_test.py query --ip <DEVICE_IP> --task-id 101
# Expected: "task not found" or similar
```

### Clear All Tasks
```bash
python3 tools/udp_countdown_test.py clear --ip <DEVICE_IP>
python3 tools/udp_countdown_test.py list --ip <DEVICE_IP>
# Expected: 0 tasks
```

---

## Test Case 8: MQTT Protocol Integration

**Objective**: Verify MQTT topic-based task creation.

### Setup MQTT Broker
Ensure MQTT broker is running and device is connected.

### Publish Add Task Command
```bash
# Using mosquitto client (adjust broker IP and topic as needed)
mosquitto_pub -h <BROKER_IP> \
  -t "iot/device/<DEVICE_MAC>/timer" \
  -m '{
    "cmd": "add_timer",
    "task_id": 401,
    "type": "once",
    "trigger_time": "2026-04-21T23:00:00",
    "power": "on",
    "mode": "cct",
    "lightness": 75,
    "cct": 4500
  }'
```

### Expected Device Behavior
- Log: `[mqtt] Timer task 401 received`
- Task added to countdown queue
- After 23:00: Light executes specified state

### Verify via UDP
```bash
python3 tools/udp_countdown_test.py query --ip <DEVICE_IP> --task-id 401
```

---

## Debugging Guide

### Common Issues

#### 1. Task Not Executing at Scheduled Time
**Check**:
1. Device time is correctly set (compare with `idf.py monitor` timestamps)
2. Task time matches device timezone (device may output logs with different TZ)
3. Device clock drifts (NTP sync issues)

**Fix**:
```bash
# Check device time in logs
idf.py monitor | grep "current time"

# Synchronize if needed (device-side implementation required)
```

#### 2. UDP Command Rejected

**Check**:
1. Device IP is correct: `ping <DEVICE_IP>`
2. Port 5569 is open: `netstat -an | grep 5569` (on device)
3. Firewall allows UDP port 5569

**Debug**:
```bash
# Send raw UDP and capture response
nc -u -l <DEVICE_IP> 5569 &  # Listen on device
python3 tools/udp_countdown_test.py add --ip <DEVICE_IP> ... # Send test

# Or use tcpdump to verify packet arrival
sudo tcpdump -i any udp port 5569
```

#### 3. BLE Frames Not Processed

**Check**:
1. Frame CRC16 is valid (script calculates automatically)
2. Session ID matches expected range (0-127, default 1)
3. Frame sequence is correct (seq increments, total consistent)
4. TLV payload contains required fields (time + state)

**Debug**:
Use `--debug` flag in BLE test script:
```bash
python3 tools/ble_countdown_test.py once ... --debug
# Shows per-frame CRC, TaskID, and structure details
```

#### 4. Tasks Not Persisting Post-Reboot

**Check**:
1. NVS partition is defined in partition table: `cat partitions.csv`
2. NVS write succeeds (check `app_countdown` logs)
3. Task count <= MAX_COUNTDOWN_TASKS_IN_MEMORY (16)

**Debug**:
```bash
# Monitor NVS writes during task addition
idf.py monitor | grep "NVS\|nvs\|flash"
```

---

## Performance Metrics

### Expected Latencies
- **UDP add task**: < 100ms
- **BLE frame processing**: Dependent on fragmentation size
- **Task execution precision**: ±1 second (loop check interval)
- **State transition**: < 50ms (device state update)

### Max Capability
- **Simultaneous tasks**: 16 (in RAM) + unlimited persistent (NVS)
- **Max task payload**: 128 bytes (TLV)
- **BLE session timeout**: 3 seconds (auto-cleanup)

---

## Success Criteria

✅ **Test 1-3**: All three protocol paths successfully queue tasks
✅ **Test 4**: Recurring (daily/weekly) tasks function correctly
✅ **Test 5**: Persistence survives device reboot
✅ **Test 6-7**: Remove/Clear operations work
✅ **Test 8**: MQTT integration functional

**If all criteria pass, countdown task system is production-ready.**

---

## Appendix: Frame Structure Reference

### UDP JSON Structure
```json
{
  "cmd": "add_timer",
  "task_id": 101,
  "type": "once|daily|weekly",
  "trigger_time": "2026-04-21T22:30:00",
  "power": "on|off",
  "mode": "cct|hsi|xy",
  "lightness": 0-100,
  "cct": 2700-7000,
  "hue": 0-360,
  "sat": 0-100,
  "x": 0-1,
  "y": 0-1
}
```

### BLE Frame Structure (10 bytes)
```
[Byte 0] Frame Type (0x30=BEGIN, 0x31=CHUNK, 0x32=COMMIT)
[Byte 1] Session ID (0-127)
[Byte 2] Seq/Index
[Byte 3] Total Chunks
[Byte 4] Timer Type (0=ONCE, 1=DAILY, 2=WEEKLY)
[Bytes 5-8] Task ID (32-bit big-endian)
[Byte 9] CRC16 High Byte
[Bytes 10-14] TLV Payload (max 5 bytes per frame)
```

### TLV Types
| Type | Code | Length | Description |
|------|------|--------|-------------|
| TIME_ABS | 0x01 | 7 | Year/month/day/time for ONCE |
| TIME_HMS | 0x02 | 3 | Hour/min/sec for DAILY/WEEKLY |
| WEEKDAY | 0x03 | 1 | Weekday (0=Sun..6=Sat) for WEEKLY |
| POWER | 0x10 | 1 | Power state (0/1) |
| MODE | 0x11 | 1 | Light mode (0=CCT, 1=HSI, 2=XY) |
| LIGHTNESS_X10 | 0x13 | 2 | 0-1000 (÷10 = 0-100%) |
| CCT | 0x14 | 2 | Color temp in Kelvin |
| HUE_X10 | 0x16 | 2 | Hue 0-3600 (÷10 = 0-360°) |
| SAT_X10 | 0x17 | 2 | Saturation 0-1000 (÷10 = 0-100%) |
| X_X10000 | 0x18 | 2 | CIE X 0-10000 (÷10000 = 0-1) |
| Y_X10000 | 0x19 | 2 | CIE Y 0-10000 (÷10000 = 0-1) |

---

## Next Steps

1. **Live Device Testing**: Flash firmware to ESP32S3 device and run Test Cases 1-8
2. **Extended Coverage**: Test with system clock changes (DST, manual adjustment)
3. **Stress Testing**: Queue 16 simultaneous tasks, verify execution order
4. **Edge Cases**: Test with invalid TLV, malformed frames, network interruptions
5. **Performance Profiling**: Measure CPU/memory overhead during task execution

