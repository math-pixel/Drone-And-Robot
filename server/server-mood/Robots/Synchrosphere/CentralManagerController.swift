// Project Synchrosphere
// Copyright 2021, Framework Labs.

import Pappe
import CoreBluetooth

/// Provides methods and activities to control the bluetooth central manager.
final class CentralManagerController : NSObject, CBCentralManagerDelegate {

    private let context: ControllerContext
    private let centralManager: CBCentralManager
    var peripheral: CBPeripheral?

    // ✅ selector actif pour filtrer correctement pendant le scan
    private var currentSelector: SyncsDeviceSelector?

    init(context: ControllerContext) {
        self.context = context
        centralManager = CBCentralManager(delegate: nil, queue: context.config.queue)
        super.init()
        centralManager.delegate = self
    }

    func makeModule(imports: [Module.Import]) -> Module {
        return Module(imports: imports) { name in

            activity (name.ScanForPeripheral_, [name.deviceSelector]) { val in
                exec  {
                    self.context.logInfo("scanning...")

                    // reset
                    self.peripheral = nil
                    self.currentSelector = (val.deviceSelector as SyncsDeviceSelector)

                    // start scan
                    self.centralManager.scanForPeripherals(withServices: [.apiService])
                }
                `defer` {
                    self.context.logInfo("stop scanning")
                    self.centralManager.stopScan()

                    // cleanup selector
                    self.currentSelector = nil
                }

                // ✅ on attend juste qu'un périphérique filtré soit sélectionné dans didDiscover
                `await` { self.peripheral != nil }

                exec { self.context.logInfo("got peripheral: \(String(describing: self.peripheral?.name))") }
            }

            activity (name.ConnectPeripheral_, []) { val in
                exec {
                    self.context.logInfo("connecting...")
                    guard let peripheral = self.peripheral else { fatalError("peripheral is nil") }
                    self.centralManager.connect(peripheral)
                }
                `await` { self.peripheral?.state == .connected }
            }

            activity (name.DisconnectPeripheral_, []) { val in
                exec {
                    self.context.logInfo("disconnecting...")
                    guard let peripheral = self.peripheral else { fatalError("peripheral is nil") }
                    self.centralManager.cancelPeripheralConnection(peripheral)
                }
                `await` { self.peripheral?.state == .disconnected }
            }
        }
    }

    var isBluetoothAvailable: Bool {
        CBManager.authorization.isOk && centralManager.state.isOk
    }

    var isPeripheralConnected: Bool {
        peripheral?.state == .connected
    }

    func requestDisconnectPeripheral() {
        context.logInfo("request disconnect peripheral")
        guard let peripheral = self.peripheral else { return }
        centralManager.cancelPeripheralConnection(peripheral)
    }

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        context.trigger()
    }

    func centralManager(_ central: CBCentralManager,
                        didDiscover peripheral: CBPeripheral,
                        advertisementData: [String : Any],
                        rssi RSSI: NSNumber) {

        // Nom fiable (souvent dans l'advertising)
        let advName = advertisementData[CBAdvertisementDataLocalNameKey] as? String
        let name = (advName ?? peripheral.name ?? "").trimmingCharacters(in: .whitespacesAndNewlines)

        self.context.logInfo("did discover \(name.isEmpty ? "\(peripheral)" : name)")

        // ✅ si on n'est pas en scan "piloté", on ignore
        guard let selector = self.currentSelector else { return }

        // ✅ on ne garde QUE si ça match le selector demandé
        guard !name.isEmpty, name.matches(selector) else { return }

        // ✅ on fige le choix (pas de overwrite par la suite)
        if self.peripheral == nil {
            self.peripheral = peripheral
            context.trigger()
        }
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        if peripheral == self.peripheral {
            self.context.logInfo("connected")
            context.trigger()
        }
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        if peripheral == self.peripheral {
            context.logInfo("disconnected, reason: \(String(describing: error))")
            context.trigger()
        }
    }
}


private extension String {
    func matches(_ selector: SyncsDeviceSelector) -> Bool {
        switch selector {
        case .named(let wanted):
            return self == wanted
        case .anyRVR, .anyMini, .anyBolt:
            guard let prefix = selector.namePrefix else { return false }
            return self.hasPrefix(prefix)
        }
    }
}

private extension CBManagerAuthorization {
    var isOk: Bool {
        return self == .allowedAlways
    }
}

private extension CBManagerState {
    var isOk: Bool {
        return self == .poweredOn
    }
}
