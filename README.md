# home-assistant-rdw
RDW sensor module for Home Assistant.

### Installation
Open a shell and go to your Home Assistant config path, and do:
```
mkdir custom_components
cd custom_components
git clone https://github.com/eelcohn/home-assistant-rdw rdw
```

### Support
Support for this module can be found in [this thread](https://community.home-assistant.io/t/custom-sensor-for-dutch-license-plate-checks-apk-check/94427)

### Configuration variables
```
plate          (Required)  Dutch license plate id
name           (Optional)  Custom name for the sensor; default value is RDW
dateformat     (Optional)  Custom date format; default format is %d-%m-%Y
scan_interval  (Optional)  Time in seconds between updates (default is 86400 seconds, which is 1 day)
binary_sensors (Optional)
  insured                  Insured flag; signals if the car is currently registered as insured (True/False)
sensors        (Optional)
  expdate                  Expire date; the date when the APK expires
  recall                   Unresolved recalls; signals if the manufacurer of the car has issued a recall because of a serious safety problem```
```

### Example code:
```
rdw:
  - plate: 16RSL9
    name: "Toyota Auris"
    dateformat: '%d %b %Y'
    sensors:
      - expdate
      - insured
      - recall
  - plate: 0001ES
    name: "Opel Kadett"
    sensors:
      - expdate
      - insured
      - recall
  - plate: 99WGDF
    name: "Vlemmix Kipper"
    sensors:
      - expdate

homeassistant:
  customize:
    sensor.bmw_expdate:
      friendly_name: "APK Vervaldatum"
    sensor.bmw_insured:
      friendly_name: "Verzekeringsstatus"
    sensor.bmw_recall:
      friendly_name: "Terugroepstatus"

automation:
    # ------------------------------------------------------- #
    # Notify 21 days before the APK date expires              #
    # ------------------------------------------------------- #
  - alias: APK date expiration notification
    trigger:
      - platform: template
        value_template: "{{ ((as_timestamp(strptime(states('sensor.toyota_auris_expdate'), '%d %b %Y')) / 86400) | int) == ((as_timestamp(strptime(states('sensor.date'), '%Y-%m-%d')) / 86400) | int) + 21 }} }}"
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: De APK keuring verloopt op {{ states.sensor.bmw_expdate.state }}. Plan een APK keuring bij de garage.

    # ------------------------------------------------------- #
    # Notify when the car's insurance has expired             #
    # ------------------------------------------------------- #
  - alias: Insurance expiration notification
    initial_state: True
    trigger:
      - platform: state
        entity_id: sensor.bmw_insured
        to: 'False'
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: De auto is niet verzekerd! Sluit een autoverzekering af voordat je ermee de weg op gaat.

    # ------------------------------------------------------- #
    # Notify when a maintenance recall has been issued        #
    # ------------------------------------------------------- #
  - alias: Recall notification
    initial_state: False
    trigger:
      - platform: state
        entity_id: sensor.bmw_recall
        to: 'True'
    action:
      - service: notify.owner
        data_template:
          title: '*Auto*'
          message: Er is een terugroepactie uitgevaardigd voor de auto. Maak een afspraak bij de garage om het probleem te verhelpen.

```
### How can I test the notifications?
##### Testing APK expiration date notification:
Pick a random license plate from https://opendata.rdw.nl/resource/m9d7-ebf2.json?vervaldatum_apk=20000222 and add it to your `configuration.yaml`
##### Testing insurance state notifications:
Pick a random license plate from https://opendata.rdw.nl/resource/m9d7-ebf2.json?wam_verzekerd=Nee and add it to your `configuration.yaml`
##### Testing unresolved recall notifications:
Pick a random license plate from https://opendata.rdw.nl/resource/t49b-isb7.json?code_status=O and add it to your `configuration.yaml`

