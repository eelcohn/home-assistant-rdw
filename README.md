# home-assistant-rdw
RDW sensor module for Home Assistant.

### Configuration variables
```
plate (Required)       Dutch license plate id
name (Optional)        Custom name for the sensor; default value is RDW
dateformat (Optional)  Custom date format; default format is %d-%m-%Y
sensors (Optional)     Sensors to display in the frontend
  expdate              Expire date; the date when the APK expires
  insured              Insured flag; signals if the car is currently registered as insured (True/False)
  recall               Recall flag; signals if the manufacurer of the car has issued a recall because of a serious safety problem```
```

### Example code:
```
sensor:
  - platform: rdw
    name: "Toyota Auris"
    plate: 16RSL9
    dateformat: '%d %b %Y'
    sensors:
      - expdate
      - insured
      - recall
  - platform: rdw
    name: "Opel Kadett"
    plate: 0001ES
    sensors:
      - expdate
      - insured
      - recall
  - platform: rdw
    name: "Vlemmix Kipper"
    plate: 99WGDF
    sensors:
      - expdate
      - insured
      - recall

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
        value_template: "{{ ((as_timestamp(strptime(states('sensor.seat_leon_expdate'), '%d %b %Y')) / 86400) | int) == ((as_timestamp(strptime(states('sensor.date'), '%Y-%m-%d')) / 86400) | int) + 21 }} }}"
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
