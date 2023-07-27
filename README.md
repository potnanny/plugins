# POTNANNY PLUGINS
Default plugins for Potnanny Greenhouse Controller System.

## Includes:

### Device Plugins
Communicating with the bluetooth devices

- Smartbot hygrometer
- Smartbot Plus hygrometer
- Xiaomi MJ-HT hygrometer
- Xiaomi Mi Flora soil sensor
- Govee H5080 bluetooth power outlet
- Govee H5082 bluetooth dual power outlet

### Pipeline Plugins
Collected device measurement data is routed through the pipeline. Any plugin that monitors this pipeline will receive data for processing.

- db.py: Write measurements to database.
- control.py: Distribute measurements to device Contol objects.


## Custom Device Plugins
End users may write their own device plugins, for interfacing with new hardware. It's easy!

### Plugin Requirements
Like the rest of Potnanny, all plugin code must be written in asyncio manner.

Plugin classes that read BLE device advertisements, should have an asyncio method named *read_advertisement* (See Smartbot Hygrometer plugins for example)

Plugin classes that connect to BLE devices as a client should have asyncio method named *poll* (see Xiaom Mi Flora plugin for example)
