import platform
import os
import socket
import subprocess
import psutil
import wmi
import win32api
import win32security
import win32com.client
import json
import datetime
import cpuinfo
import GPUtil
from typing import Dict, Any

class WindowsSystemInfo:
    def __init__(self):
        self.info = {}
        self.c = wmi.WMI()
        self.computer_name = socket.gethostname()
        
    def get_all_info(self) -> Dict[str, Any]:
        """Get all system information"""
        
        print("[*] Gathering Windows System Information...")
        
        self.get_basic_info()
        self.get_os_info()
        self.get_hardware_info()
        self.get_cpu_info()
        self.get_memory_info()
        self.get_disk_info()
        self.get_gpu_info()
        self.get_network_info()
        self.get_users_info()
        self.get_installed_software()
        self.get_running_processes()
        self.get_services_info()
        self.get_startup_programs()
        self.get_environment_variables()
        self.get_scheduled_tasks()
        self.get_event_logs_summary()
        self.get_security_info()
        self.get_performance_info()
        self.get_bios_info()
        self.get_drivers_info()
        self.get_hotfixes_info()
        self.get_usb_devices()
        self.get_printers_info()
        self.get_shared_resources()
        
        return self.info
    
    def get_basic_info(self):
        """Basic system information"""
        print("  - Basic Info")
        self.info['basic'] = {
            'computer_name': self.computer_name,
            'user_name': os.getenv('USERNAME'),
            'user_domain': os.getenv('USERDOMAIN'),
            'system_root': os.getenv('SystemRoot'),
            'processor_arch': os.getenv('PROCESSOR_ARCHITECTURE'),
            'number_of_processors': os.getenv('NUMBER_OF_PROCESSORS'),
            'processor_identifier': os.getenv('PROCESSOR_IDENTIFIER'),
        }
    
    def get_os_info(self):
        """Operating system information"""
        print("  - OS Information")
        try:
            os_info = self.c.Win32_OperatingSystem()[0]
            cs_info = self.c.Win32_ComputerSystem()[0]
            
            self.info['os'] = {
                'name': os_info.Name.split('|')[0],
                'version': os_info.Version,
                'build_number': os_info.BuildNumber,
                'architecture': os_info.OSArchitecture,
                'install_date': str(os_info.InstallDate),
                'last_boot': str(os_info.LastBootUpTime),
                'manufacturer': os_info.Manufacturer,
                'registered_user': os_info.RegisteredUser,
                'serial_number': os_info.SerialNumber,
                'system_directory': os_info.SystemDirectory,
                'total_visible_memory': f"{int(os_info.TotalVisibleMemorySize) // 1024} MB",
                'free_physical_memory': f"{int(os_info.FreePhysicalMemory) // 1024} MB",
                'total_virtual_memory': f"{int(os_info.TotalVirtualMemorySize) // 1024} MB",
                'free_virtual_memory': f"{int(os_info.FreeVirtualMemory) // 1024} MB",
                'max_processes': os_info.MaxNumberOfProcesses,
                'max_process_memory': os_info.MaxProcessMemorySize,
                'current_time_zone': os_info.CurrentTimeZone,
                'country_code': os_info.CountryCode,
                'os_language': os_info.OSLanguage,
                'os_product_suite': os_info.OSProductSuite,
                'os_type': os_info.OSType,
                'other_type_description': os_info.OtherTypeDescription,
                'primary': str(os_info.Primary),
                'service_pack_major': os_info.ServicePackMajorVersion,
                'service_pack_minor': os_info.ServicePackMinorVersion,
                'windows_directory': os_info.WindowsDirectory,
            }
            
            # Domain info
            self.info['os']['domain'] = cs_info.Domain
            self.info['os']['domain_role'] = cs_info.DomainRole
            self.info['os']['part_of_domain'] = cs_info.PartOfDomain
            self.info['os']['workgroup'] = cs_info.Workgroup
            
        except Exception as e:
            self.info['os'] = {'error': str(e)}
    
    def get_hardware_info(self):
        """Hardware information"""
        print("  - Hardware Information")
        try:
            cs_info = self.c.Win32_ComputerSystem()[0]
            self.info['hardware'] = {
                'manufacturer': cs_info.Manufacturer,
                'model': cs_info.Model,
                'system_type': cs_info.SystemType,
                'total_physical_memory': f"{int(cs_info.TotalPhysicalMemory) // (1024**3)} GB",
                'number_of_processors': cs_info.NumberOfProcessors,
                'number_of_logical_processors': cs_info.NumberOfLogicalProcessors,
                'primary_owner_name': cs_info.PrimaryOwnerName,
                'chassis_serial_number': cs_info.ChassisSerialNumber,
            }
        except Exception as e:
            self.info['hardware'] = {'error': str(e)}
    
    def get_cpu_info(self):
        """CPU detailed information"""
        print("  - CPU Information")
        try:
            cpus = []
            for cpu in self.c.Win32_Processor():
                cpu_info = {
                    'name': cpu.Name.strip(),
                    'manufacturer': cpu.Manufacturer,
                    'caption': cpu.Caption,
                    'device_id': cpu.DeviceID,
                    'description': cpu.Description,
                    'architecture': cpu.Architecture,
                    'address_width': cpu.AddressWidth,
                    'current_clock_speed': f"{cpu.CurrentClockSpeed} MHz",
                    'max_clock_speed': f"{cpu.MaxClockSpeed} MHz",
                    'ext_clock_speed': f"{cpu.ExtClockSpeed} MHz",
                    'l2_cache_size': f"{cpu.L2CacheSize} KB",
                    'l3_cache_size': f"{cpu.L3CacheSize} KB",
                    'core_count': cpu.NumberOfCores,
                    'logical_processors': cpu.NumberOfLogicalProcessors,
                    'processor_id': cpu.ProcessorId,
                    'status': cpu.Status,
                    'voltage': cpu.CurrentVoltage,
                    'load_percentage': cpu.LoadPercentage,
                }
                cpus.append(cpu_info)
            self.info['cpu'] = cpus
        except Exception as e:
            self.info['cpu'] = {'error': str(e)}
    
    def get_memory_info(self):
        """Memory/RAM information"""
        print("  - Memory Information")
        try:
            memory = []
            total_size = 0
            for mem in self.c.Win32_PhysicalMemory():
                mem_info = {
                    'manufacturer': mem.Manufacturer,
                    'capacity': f"{int(mem.Capacity) // (1024**3)} GB",
                    'speed': f"{mem.Speed} MHz",
                    'memory_type': mem.MemoryType,
                    'form_factor': mem.FormFactor,
                    'device_locator': mem.DeviceLocator,
                    'bank_label': mem.BankLabel,
                    'configured_clock_speed': f"{mem.ConfiguredClockSpeed} MHz",
                    'max_voltage': mem.MaxVoltage,
                    'min_voltage': mem.MinVoltage,
                    'configured_voltage': mem.ConfiguredVoltage,
                    'data_width': f"{mem.DataWidth} bits",
                    'total_width': f"{mem.TotalWidth} bits",
                }
                total_size += int(mem.Capacity)
                memory.append(mem_info)
            
            self.info['memory'] = {
                'modules': memory,
                'total_physical_memory': f"{total_size // (1024**3)} GB",
                'virtual_memory_total': f"{psutil.virtual_memory().total // (1024**3)} GB",
                'virtual_memory_available': f"{psutil.virtual_memory().available // (1024**3)} GB",
                'virtual_memory_percent_used': psutil.virtual_memory().percent,
            }
        except Exception as e:
            self.info['memory'] = {'error': str(e)}
    
    def get_disk_info(self):
        """Disk/Storage information"""
        print("  - Disk Information")
        try:
            disks = []
            for disk in self.c.Win32_DiskDrive():
                partitions = []
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        partitions.append({
                            'drive': logical.DeviceID,
                            'filesystem': logical.FileSystem,
                            'total_size': f"{int(logical.Size) // (1024**3)} GB" if logical.Size else 'N/A',
                            'free_space': f"{int(logical.FreeSpace) // (1024**3)} GB" if logical.FreeSpace else 'N/A',
                            'volume_name': logical.VolumeName,
                            'serial_number': logical.VolumeSerialNumber,
                        })
                
                disk_info = {
                    'model': disk.Model,
                    'manufacturer': disk.Manufacturer,
                    'interface': disk.InterfaceType,
                    'media_type': disk.MediaType,
                    'size': f"{int(disk.Size) // (1024**3)} GB" if disk.Size else 'N/A',
                    'partitions': partitions,
                    'serial_number': disk.SerialNumber,
                    'firmware_revision': disk.FirmwareRevision,
                    'status': disk.Status,
                    'index': disk.Index,
                }
                disks.append(disk_info)
            
            self.info['disks'] = disks
        except Exception as e:
            self.info['disks'] = {'error': str(e)}
    
    def get_gpu_info(self):
        """Graphics card information"""
        print("  - GPU Information")
        try:
            gpus = []
            for gpu in self.c.Win32_VideoController():
                gpu_info = {
                    'name': gpu.Name,
                    'adapter_ram': f"{int(gpu.AdapterRAM) // (1024**2)} MB" if gpu.AdapterRAM else 'N/A',
                    'driver_version': gpu.DriverVersion,
                    'driver_date': gpu.DriverDate,
                    'video_processor': gpu.VideoProcessor,
                    'video_architecture': gpu.VideoArchitecture,
                    'video_memory_type': gpu.VideoMemoryType,
                    'current_horizontal_resolution': gpu.CurrentHorizontalResolution,
                    'current_vertical_resolution': gpu.CurrentVerticalResolution,
                    'current_refresh_rate': f"{gpu.CurrentRefreshRate} Hz",
                    'status': gpu.Status,
                }
                gpus.append(gpu_info)
            
            # Try with GPUtil for NVIDIA GPUs
            try:
                gpus_nvidia = GPUtil.getGPUs()
                for i, gpu in enumerate(gpus_nvidia):
                    if i < len(gpus):
                        gpus[i].update({
                            'load': f"{gpu.load * 100:.1f}%",
                            'memory_used': f"{gpu.memoryUsed} MB",
                            'memory_total': f"{gpu.memoryTotal} MB",
                            'temperature': f"{gpu.temperature} °C",
                        })
            except:
                pass
                
            self.info['gpu'] = gpus
        except Exception as e:
            self.info['gpu'] = {'error': str(e)}
    
    def get_network_info(self):
        """Network interfaces information"""
        print("  - Network Information")
        try:
            networks = []
            for nic in self.c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                net_info = {
                    'description': nic.Description,
                    'mac_address': nic.MACAddress,
                    'ip_addresses': nic.IPAddress,
                    'subnet_masks': nic.IPSubnet,
                    'default_gateways': nic.DefaultIPGateway,
                    'dns_servers': nic.DNSServerSearchOrder,
                    'dhcp_enabled': nic.DHCPEnabled,
                    'dhcp_server': nic.DHCPServer,
                    'wins_primary': nic.WINSPrimaryServer,
                    'wins_secondary': nic.WINSSecondaryServer,
                    'interface_index': nic.InterfaceIndex,
                }
                networks.append(net_info)
            
            # Add network statistics
            net_io = psutil.net_io_counters()
            self.info['network'] = {
                'interfaces': networks,
                'bytes_sent': net_io.bytes_sent,
                'bytes_received': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_received': net_io.packets_recv,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout,
                'drops_in': net_io.dropin,
                'drops_out': net_io.dropout,
            }
        except Exception as e:
            self.info['network'] = {'error': str(e)}
    
    def get_users_info(self):
        """User accounts information"""
        print("  - User Information")
        try:
            users = []
            for user in self.c.Win32_UserAccount():
                user_info = {
                    'name': user.Name,
                    'domain': user.Domain,
                    'full_name': user.FullName,
                    'disabled': user.Disabled,
                    'locked': user.Locked,
                    'password_changeable': user.PasswordChangeable,
                    'password_expires': user.PasswordExpires,
                    'password_required': user.PasswordRequired,
                    'sid': user.SID,
                    'status': user.Status,
                    'account_type': user.AccountType,
                    'description': user.Description,
                }
                users.append(user_info)
            
            # Current logged in users
            logged_users = []
            for user in psutil.users():
                logged_users.append({
                    'name': user.name,
                    'terminal': user.terminal,
                    'host': user.host,
                    'started': datetime.datetime.fromtimestamp(user.started).strftime('%Y-%m-%d %H:%M:%S'),
                    'pid': user.pid,
                })
            
            self.info['users'] = {
                'all_accounts': users,
                'logged_in': logged_users,
            }
        except Exception as e:
            self.info['users'] = {'error': str(e)}
    
    def get_installed_software(self):
        """Installed software information"""
        print("  - Installed Software")
        try:
            software = []
            # Using registry method (faster)
            import winreg
            
            def get_installed_from_registry(key, subkey):
                try:
                    with winreg.OpenKey(key, subkey, 0, winreg.KEY_READ) as regkey:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(regkey, i)
                                with winreg.OpenKey(regkey, subkey_name) as subsubkey:
                                    try:
                                        name, _ = winreg.QueryValueEx(subsubkey, "DisplayName")
                                        version, _ = winreg.QueryValueEx(subsubkey, "DisplayVersion")
                                        publisher, _ = winreg.QueryValueEx(subsubkey, "Publisher")
                                        install_date, _ = winreg.QueryValueEx(subsubkey, "InstallDate")
                                        
                                        software.append({
                                            'name': name,
                                            'version': version,
                                            'publisher': publisher,
                                            'install_date': install_date,
                                            'uninstall_string': subkey_name,
                                        })
                                    except:
                                        pass
                            except WindowsError:
                                break
                            i += 1
                except:
                    pass
            
            # Check 64-bit and 32-bit registry locations
            get_installed_from_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            get_installed_from_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")
            get_installed_from_registry(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            
            self.info['software'] = sorted(software, key=lambda x: x['name'])
        except Exception as e:
            self.info['software'] = {'error': str(e)}
    
    def get_running_processes(self):
        """Running processes information"""
        print("  - Running Processes")
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'exe', 'status']):
                try:
                    pinfo = proc.info
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'username': pinfo['username'],
                        'cpu_percent': pinfo['cpu_percent'],
                        'memory_percent': pinfo['memory_percent'],
                        'create_time': datetime.datetime.fromtimestamp(pinfo['create_time']).strftime('%Y-%m-%d %H:%M:%S') if pinfo['create_time'] else None,
                        'exe': pinfo['exe'],
                        'status': pinfo['status'],
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            self.info['processes'] = {
                'count': len(processes),
                'list': sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:50],  # Top 50 by CPU
            }
        except Exception as e:
            self.info['processes'] = {'error': str(e)}
    
    def get_services_info(self):
        """Windows services information"""
        print("  - Services")
        try:
            services = []
            for service in self.c.Win32_Service():
                services.append({
                    'name': service.Name,
                    'display_name': service.DisplayName,
                    'description': service.Description,
                    'state': service.State,
                    'start_mode': service.StartMode,
                    'start_name': service.StartName,
                    'path_name': service.PathName,
                    'process_id': service.ProcessId,
                    'service_type': service.ServiceType,
                    'status': service.Status,
                })
            
            self.info['services'] = {
                'total': len(services),
                'running': len([s for s in services if s['state'] == 'Running']),
                'stopped': len([s for s in services if s['state'] == 'Stopped']),
                'list': services,
            }
        except Exception as e:
            self.info['services'] = {'error': str(e)}
    
    def get_startup_programs(self):
        """Startup programs information"""
        print("  - Startup Programs")
        try:
            startup = []
            
            # Current user startup
            user_startup = os.path.join(os.getenv('APPDATA'), 
                                        'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
            if os.path.exists(user_startup):
                for item in os.listdir(user_startup):
                    startup.append({
                        'location': 'Current User Startup',
                        'name': item,
                        'path': os.path.join(user_startup, item)
                    })
            
            # All users startup
            all_startup = os.path.join(os.getenv('PROGRAMDATA'), 
                                      'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
            if os.path.exists(all_startup):
                for item in os.listdir(all_startup):
                    startup.append({
                        'location': 'All Users Startup',
                        'name': item,
                        'path': os.path.join(all_startup, item)
                    })
            
            # Registry startup entries
            import winreg
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
            ]
            
            for hkey, path in reg_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                startup.append({
                                    'location': f"{'HKLM' if hkey == winreg.HKEY_LOCAL_MACHINE else 'HKCU'}:{path}",
                                    'name': name,
                                    'command': value,
                                })
                                i += 1
                            except WindowsError:
                                break
                except:
                    pass
            
            self.info['startup'] = startup
        except Exception as e:
            self.info['startup'] = {'error': str(e)}
    
    def get_environment_variables(self):
        """Environment variables"""
        print("  - Environment Variables")
        try:
            env_vars = {}
            for key, value in os.environ.items():
                env_vars[key] = value
            
            self.info['environment'] = env_vars
        except Exception as e:
            self.info['environment'] = {'error': str(e)}
    
    def get_scheduled_tasks(self):
        """Scheduled tasks information"""
        print("  - Scheduled Tasks")
        try:
            # Using PowerShell for more complete info
            ps_script = """
            Get-ScheduledTask | ForEach-Object {
                $task = $_
                $info = @{
                    TaskName = $task.TaskName
                    TaskPath = $task.TaskPath
                    State = $task.State
                    Description = (Get-ScheduledTaskInfo $task).Description
                    LastRunTime = (Get-ScheduledTaskInfo $task).LastRunTime
                    LastTaskResult = (Get-ScheduledTaskInfo $task).LastTaskResult
                    NextRunTime = (Get-ScheduledTaskInfo $task).NextRunTime
                }
                $info | ConvertTo-Json
            }
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                tasks = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        try:
                            tasks.append(json.loads(line))
                        except:
                            pass
                self.info['scheduled_tasks'] = tasks
            else:
                self.info['scheduled_tasks'] = {'error': 'Failed to get scheduled tasks'}
        except Exception as e:
            self.info['scheduled_tasks'] = {'error': str(e)}
    
    def get_event_logs_summary(self):
        """Event logs summary"""
        print("  - Event Logs Summary")
        try:
            logs = []
            for log in self.c.Win32_NTEventLogFile():
                logs.append({
                    'name': log.LogfileName,
                    'max_size': f"{log.MaxFileSize} bytes",
                    'number_of_records': log.NumberOfRecords,
                    'overwrite_policy': log.OverwritePolicy,
                    'file_size': f"{log.FileSize} bytes",
                    'path': log.Name,
                })
            
            self.info['event_logs'] = logs
        except Exception as e:
            self.info['event_logs'] = {'error': str(e)}
    
    def get_security_info(self):
        """Security related information"""
        print("  - Security Information")
        try:
            security_info = {
                'uac_enabled': self.get_uac_status(),
                'firewall_status': self.get_firewall_status(),
                'antivirus': self.get_antivirus_info(),
                'bitlocker_status': self.get_bitlocker_status(),
                'secure_boot': self.get_secure_boot_status(),
            }
            self.info['security'] = security_info
        except Exception as e:
            self.info['security'] = {'error': str(e)}
    
    def get_uac_status(self):
        """Check UAC status"""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as key:
                value, _ = winreg.QueryValueEx(key, "EnableLUA")
                return value == 1
        except:
            return None
    
    def get_firewall_status(self):
        """Check Windows Firewall status"""
        try:
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles'],
                capture_output=True,
                text=True
            )
            return 'ON' if 'ON' in result.stdout else 'OFF'
        except:
            return None
    
    def get_antivirus_info(self):
        """Get antivirus information"""
        try:
            antivirus = []
            for product in self.c.Win32_Product():
                if 'antivirus' in product.Name.lower() or 'security' in product.Name.lower():
                    antivirus.append({
                        'name': product.Name,
                        'version': product.Version,
                        'vendor': product.Vendor,
                    })
            return antivirus
        except:
            return None
    
    def get_bitlocker_status(self):
        """Check BitLocker status"""
        try:
            result = subprocess.run(
                ['manage-bde', '-status'],
                capture_output=True,
                text=True
            )
            return result.stdout
        except:
            return None
    
    def get_secure_boot_status(self):
        """Check Secure Boot status"""
        try:
            result = subprocess.run(
                ['powershell', 'Confirm-SecureBootUEFI'],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            return None
    
    def get_performance_info(self):
        """Current performance information"""
        print("  - Performance Information")
        try:
            self.info['performance'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'cpu_percent_per_core': psutil.cpu_percent(interval=1, percpu=True),
                'cpu_freq_current': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'cpu_freq_min': psutil.cpu_freq().min if psutil.cpu_freq() else None,
                'cpu_freq_max': psutil.cpu_freq().max if psutil.cpu_freq() else None,
                'memory_percent': psutil.virtual_memory().percent,
                'swap_memory_percent': psutil.swap_memory().percent,
                'disk_usage': self.get_disk_usage(),
                'network_connections': len(psutil.net_connections()),
                'boot_time': datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
            }
        except Exception as e:
            self.info['performance'] = {'error': str(e)}
    
    def get_disk_usage(self):
        """Get disk usage for all drives"""
        usage = {}
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                usage[partition.mountpoint] = {
                    'total': f"{partition_usage.total // (1024**3)} GB",
                    'used': f"{partition_usage.used // (1024**3)} GB",
                    'free': f"{partition_usage.free // (1024**3)} GB",
                    'percent': partition_usage.percent,
                    'filesystem': partition.fstype,
                }
            except PermissionError:
                usage[partition.mountpoint] = {'error': 'Permission denied'}
        return usage
    
    def get_bios_info(self):
        """BIOS information"""
        print("  - BIOS Information")
        try:
            bios = self.c.Win32_BIOS()[0]
            self.info['bios'] = {
                'manufacturer': bios.Manufacturer,
                'name': bios.Name,
                'version': bios.Version,
                'serial_number': bios.SerialNumber,
                'release_date': str(bios.ReleaseDate),
                'smbios_version': bios.SMBIOSBIOSVersion,
                'status': bios.Status,
            }
        except Exception as e:
            self.info['bios'] = {'error': str(e)}
    
    def get_drivers_info(self):
        """Device drivers information"""
        print("  - Drivers Information")
        try:
            drivers = []
            for driver in self.c.Win32_SystemDriver():
                drivers.append({
                    'name': driver.Name,
                    'display_name': driver.DisplayName,
                    'description': driver.Description,
                    'state': driver.State,
                    'start_mode': driver.StartMode,
                    'path': driver.PathName,
                    'service_type': driver.ServiceType,
                    'status': driver.Status,
                })
            self.info['drivers'] = drivers
        except Exception as e:
            self.info['drivers'] = {'error': str(e)}
    
    def get_hotfixes_info(self):
        """Installed hotfixes/updates"""
        print("  - Hotfixes/Updates")
        try:
            hotfixes = []
            for hotfix in self.c.Win32_QuickFixEngineering():
                hotfixes.append({
                    'hotfix_id': hotfix.HotFixID,
                    'description': hotfix.Description,
                    'installed_on': hotfix.InstalledOn,
                    'installed_by': hotfix.InstalledBy,
                    'service_pack': hotfix.ServicePackInEffect,
                })
            self.info['hotfixes'] = hotfixes
        except Exception as e:
            self.info['hotfixes'] = {'error': str(e)}
    
    def get_usb_devices(self):
        """USB devices information"""
        print("  - USB Devices")
        try:
            usb_devices = []
            for usb in self.c.Win32_USBHub():
                usb_devices.append({
                    'device_id': usb.DeviceID,
                    'description': usb.Description,
                    'name': usb.Name,
                    'status': usb.Status,
                })
            self.info['usb_devices'] = usb_devices
        except Exception as e:
            self.info['usb_devices'] = {'error': str(e)}
    
    def get_printers_info(self):
        """Printers information"""
        print("  - Printers")
        try:
            printers = []
            for printer in self.c.Win32_Printer():
                printers.append({
                    'name': printer.Name,
                    'driver_name': printer.DriverName,
                    'port_name': printer.PortName,
                    'shared': printer.Shared,
                    'share_name': printer.ShareName,
                    'location': printer.Location,
                    'status': printer.Status,
                    'default': printer.Default,
                    'network': printer.Network,
                })
            self.info['printers'] = printers
        except Exception as e:
            self.info['printers'] = {'error': str(e)}
    
    def get_shared_resources(self):
        """Shared resources"""
        print("  - Shared Resources")
        try:
            shares = []
            for share in self.c.Win32_Share():
                shares.append({
                    'name': share.Name,
                    'path': share.Path,
                    'description': share.Description,
                    'type': share.Type,
                    'maximum_allowed': share.MaximumAllowed,
                    'install_date': str(share.InstallDate) if share.InstallDate else None,
                })
            self.info['shares'] = shares
        except Exception as e:
            self.info['shares'] = {'error': str(e)}

    def save_to_file(self, filename='windows_info.json'):
        """Save all information to a JSON file"""
        print(f"\n[*] Saving to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.info, f, indent=2, default=str, ensure_ascii=False)
        print(f"[+] Saved to {filename}")
    
    def print_summary(self):
        """Print a summary of the system"""
        print("\n" + "="*80)
        print(f"WINDOWS SYSTEM INFORMATION SUMMARY - {self.computer_name}")
        print("="*80)
        
        if 'os' in self.info:
            os_info = self.info['os']
            print(f"OS: {os_info.get('name', 'N/A')}")
            print(f"Version: {os_info.get('version', 'N/A')} (Build {os_info.get('build_number', 'N/A')})")
            print(f"Architecture: {os_info.get('architecture', 'N/A')}")
            print(f"Last Boot: {os_info.get('last_boot', 'N/A')}")
        
        if 'hardware' in self.info:
            hw = self.info['hardware']
            print(f"\nHardware: {hw.get('manufacturer', 'N/A')} {hw.get('model', 'N/A')}")
            print(f"Memory: {hw.get('total_physical_memory', 'N/A')}")
        
        if 'cpu' in self.info and self.info['cpu']:
            if isinstance(self.info['cpu'], list) and self.info['cpu']:
                cpu = self.info['cpu'][0]
                print(f"\nCPU: {cpu.get('name', 'N/A')}")
                print(f"Cores: {cpu.get('core_count', 'N/A')} physical, {cpu.get('logical_processors', 'N/A')} logical")
        
        if 'gpu' in self.info and self.info['gpu']:
            if isinstance(self.info['gpu'], list) and self.info['gpu']:
                gpu = self.info['gpu'][0]
                print(f"GPU: {gpu.get('name', 'N/A')}")
        
        if 'disks' in self.info and self.info['disks']:
            total_storage = 0
            for disk in self.info['disks']:
                if 'size' in disk and disk['size'] != 'N/A':
                    try:
                        size_gb = int(disk['size'].split()[0])
                        total_storage += size_gb
                    except:
                        pass
            print(f"Total Storage: ~{total_storage} GB")
        
        if 'users' in self.info:
            users = self.info['users']
            print(f"\nUser Accounts: {len(users.get('all_accounts', []))}")
            print(f"Logged In: {len(users.get('logged_in', []))}")
        
        if 'processes' in self.info:
            print(f"Running Processes: {self.info['processes'].get('count', 0)}")
        
        if 'services' in self.info:
            services = self.info['services']
            print(f"Services: {services.get('running', 0)} running, {services.get('stopped', 0)} stopped")
        
        if 'software' in self.info and not isinstance(self.info['software'], dict):
            print(f"Installed Software: {len(self.info['software'])} applications")
        
        print("="*80)

def main():
    """Main function to run the system information gatherer"""
    print("[+] Windows System Information Gatherer")
    print("[+] Initializing...")
    
    # Create instance and gather all info
    sysinfo = WindowsSystemInfo()
    
    try:
        info = sysinfo.get_all_info()
        
        # Print summary
        sysinfo.print_summary()
        
        # Save to file
        sysinfo.save_to_file('windows_system_info.json')
        
        # Also save a readable text version
        with open('windows_system_info.txt', 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"WINDOWS SYSTEM INFORMATION REPORT\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            for category, data in info.items():
                f.write(f"\n{category.upper()}\n")
                f.write("-" * 40 + "\n")
                if isinstance(data, dict) and 'error' in data:
                    f.write(f"Error: {data['error']}\n")
                elif isinstance(data, list):
                    for i, item in enumerate(data[:10]):  # First 10 items
                        f.write(f"{i+1}. {item}\n")
                    if len(data) > 10:
                        f.write(f"... and {len(data)-10} more\n")
                elif isinstance(data, dict):
                    for key, value in data.items():
                        if not isinstance(value, (list, dict)):
                            f.write(f"{key}: {value}\n")
                f.write("\n")
        
        print(f"\n[+] Text report saved to windows_system_info.txt")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        print(f"\n[!] Error: {e}")

if __name__ == "__main__":
    main()