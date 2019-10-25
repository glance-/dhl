Postnord custom_component
=========================

This is a custom component for home-assistant to track postnord packages.

Its activated by adding the following to your configuration.yaml:
```yaml
sensor:
  - platform: postnord
    api_key: !secret postnord_api_key
```
And you get your own api key by registering at https://developer.postnord.com/


After that you can start to track your packages by calling the service
`postnord.register`  with a argument looking like
`{"package_id": "UA123456789SE"}` to have home-assistant start tracking
that package.

And when you loose interest in that package, you just stop tracking it by
calling `postnord.unregister` with a corresponding argument.


To view all your packages in a nice fashion, I use the custom-group-card[1]
to view them all as a list in lovelace:
```yaml
      - type: 'custom:group-card'
        group: group.all_postnord_packages
```


1. https://github.com/custom-cards/group-card
