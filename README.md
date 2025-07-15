# roomba_rest980

Drop-in native integration/replacement for [jerrywillans/ha-rest980-roomba](https://github.com/jeremywillans/ha-rest980-roomba).

Still work in progress, but the vacuum entity has been fully ported over.

## Roadmap

- [x] Feature parity (minus actions) with vacuum entity
- [ ] Actions
- [ ] Dynamically grab rooms and add them to the UI

## Setup

### Prerequisites / Recommendations

- HACS
- rest980
  - If you don't have it yet, don't worry; this guide will show you how to add it.
- Rooms mapped/setup in iRobot app
  - Note that everytime you remap and a room changes, it's ID may change!
- Knowledge of your Roomba's IP

> I recommend that you use [the lovelace-roomba-vacuum-card](https://github.com/jeremywillans/lovelace-roomba-vacuum-card) until I remake it for this integration.


## Step 1: Setting up rest980: Grab Robot Credentials

If you already have it setup, and you know its url (like `http://localhost:3000`), you may skip this step.  
First, you must gather your robot's on-device password and BLID (identifier).

> NOTE: You cannot have the iRobot app running on your phone, or anything else connected to it during this step!

<details open>
  <summary>
  For Docker users
  </summary>
Execute this command:  
```sh
docker run -it node sh -c "npm install -g dorita980 && get-roomba-password <robotIP>"
```
and follow the on-screen instructions.
</details>

<details>
  <summary>
  HA Addon by jeremywillans
  </summary>

Add `https://github.com/jeremywillans/hass-addons` to the Addons tab.
Locate and install the `roombapw` addon, following the included instructions.

</details>

<details>
  <summary>
  Other HA installation method
  </summary>

If you dont have direct access to Docker, you can clone and install the dorita980 package locally.  
See [dorita980's instructions on how to get the credentials](https://github.com/koalazak/dorita980#how-to-get-your-usernameblid-and-password).

</details>

### Setting up rest980: Bringing The Server Up

Now that you have your robot's IP, BLID, and password, we need to actually start rest980.

<details open>
  <summary>
  For Docker users (docker-compose)
  </summary>

[Download the docker-compose.yaml file, and bring the service up.](docker-compose.yaml)

To bring the service up (just rest980) and leave it in the background, run

```sh
docker-compose up -d rest980
```

You may also add the service to an existing configuration. You do not need to add file binds/mounts, as there are not any.

</details>

<details>
  <summary>
  HA Addon by jeremywillans
  </summary>

If you haven't, add `https://github.com/jeremywillans/hass-addons` to the Addons tab.
Locate and install the `rest980` addon, then update and save the configuration options with the credentials you got from the previous step.
> NOTE: Rest980 Firmware option 2 implies v2+ (inclusive of 3.x)

</details>

<details>
  <summary>
    Other HA installation method
  </summary>

  Clone and start the [rest980 server by koalazak, and note your computer's IP and port.](https://github.com/koalazak/rest980)

</details>

## Step 2: Setting up the Integration

<details open>
  <summary>
  For HACS users
  </summary>
  Add this custom repository, `https://github.com/ia74/roomba_rest980` to HACS as an Integration. Search for the addon ("iRobot Roomba (rest980)")
</details>

<details>
  <summary>
  Manual installation
  </summary>
  Clone this repository, `https://github.com/ia74/roomba_rest980`, and add the custom component folder (`roomba_rest980`) to your Home Assistant's `config/custom_components` folder.
</details>