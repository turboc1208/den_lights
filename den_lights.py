import my_appapi as appapi
             
class den_lights(appapi.my_appapi):

  def initialize(self):
    # self.LOGLEVEL="DEBUG"
    self.log("den_lights App")

    ######################### Values to move to config file or somewhere.
    self.light_max=128
    self.light_dim=32

    self.hi_temp=75
    self.lo_temp=73

    self.targets={"light.den_light_level":{"triggers":{"light.den_light_level":{"type":"light","bit":32,"onValue":"on"},
                                                        "input_boolean.someone_home":{"type":"tracker","bit":1,"onValue":"on"},
                                                        "media_player.dentv":{"type":"media","bit":8,"onValue":"on"},
                                                        "input_boolean.denmotion":{"type":"motion","bit":2,"onValue":"on"}},
                                            "type":"light",
                                            "onState":[33,34,35,37,38,39,41,42,43,45,46,47,49,50,51,53,54,55,57,58,59,61,62,63,97,98,99,101,102,103,105,106,107,109,110,111,113,114,115,117,118,119,121,122,123,125,126,127],
                                            "dimState":[41,42,43,45,46,47,57,58,59,61,62,63,105,106,107,109,110,111,121,122,123,125,126,127],
                                            "callback":self.light_state_handler,
                                            "overrides":["input_boolean.party_override"]},
                 "fan.den_fan_level":{"triggers":{"fan.den_fan_level":{"type":"fan","bit":16,"onValue":"on"},
                                                     "sensor.den_sensor_temperature":{"type":"temperature","bit":4,"onValue":"on"},
                                                     "input_boolean.someone_home":{"type":"tracker","bit":1,"onValue":"home"}},
                                         "type":"fan",
                                         "onState":[4,5,6,7,12,13,14,15,20,21,22,23,28,29,30,31,36,37,38,39,44,45,46,47,52,53,54,55,
                                                    60,61,62,63,68,69,70,71,76,77,78,79,84,85,86,87,92,93,94,95,100,101,102,103,
                                                    108,109,110,111,116,117,118,119,124,125,126,127],
                                         "dimState":[0],
                                         "callback":self.light_state_handler,
                                         "overrides":["input_boolean.party_override"]}}
  
    #################End of values to move to config file or somewhere.

    for ent in self.targets:
      for ent_trigger in self.targets[ent]["triggers"]:
        self.log("registering callback for {} on {} for target {}".format(ent_trigger,self.targets[ent]["callback"],ent))
        self.listen_state(self.targets[ent]["callback"],ent_trigger,target=ent)
      self.process_light_state(ent)      # process each light as we register a callback for it's triggers rather than wait for a trigger to fire first.

  ########
  #
  # state change handler.  All it does is call process_light_state all the work is done there.
  #
  def light_state_handler(self,trigger,attr,old,new,kwargs):
    self.process_light_state(kwargs["target"],old,new)


  ########
  #
  # process_light_state.  All the light processing happens in here.
  #
  def process_light_state(self,target,old="o_unk",new="n_unk",**kwargs):
    # build current state binary flag.
    state=0
    type_bits={}
    
    # here we are building a binary flag/mask that represents the current state of the triggers that impact our target light.
    # one bit for each trigger.
    # bits are assigned in targets dictionary.

    for trigger in self.targets[target]["triggers"]:      # loop through triggers
      trigger_type = self.targets[target]["triggers"][trigger]["type"]
      onValue = self.targets[target]["triggers"][trigger]["onValue"]
      bit = self.targets[target]["triggers"][trigger]["bit"]
      trigger_state = self.normalize_state(target,trigger,trigger_type)
    
      # logical "or" value for this trigger to existing state bits.
      state=state | (bit if (trigger_state==onValue) else 0)

      # typebits is a quick access array that takes the friendly type of the trigger and associates it with it's bit
      # it's just to make it easier to search later.
      type_bits[trigger_type]=bit


    if not self.check_overide_active(target):               # if the override bit is set, then don't evaluate anything else.  Think of it as manual mode.
      if not state in self.targets[target]["onState"]:     # if its not in on its off these states always result in light being turned off
        self.log("state = {} turning off light".format(state))
        self.turn_off(target)
      elif state in self.targets[target]["onState"]:    # these states always result in light being turned on.
        self.log("state = {} turning on light".format(state))
        if state in self.targets[target]["dimState"]:                      # when turning on lights, media player determines whether to dim or not.
          self.log("media player involved so dim lights")
          self.turn_on(target,brightness=self.light_dim)
        else:                                                   # it wasn't a media player dim situation so it's just a simple turn on the light.
          self.log("state={} turning on light".format(state))
          if old!=new:
            self.turn_on(target,brightness=self.light_max)
          else:
            self.log("old={} new={} - same state when attempting turn on".format(old,new))
    else:
      self.log("home override set so no automations performed")

  #############
  #
  # normalize_state - take incoming states and convert any that are calculated to on/off values.
  #
  def normalize_state(self,target,trigger,type):
    self.log("about to get state for {}, {}, {}, {}".format(trigger,type,self.lo_temp,self.hi_temp))
    newstate=self.get_state(trigger,type=type,min=self.lo_temp,max=self.hi_temp)
    if newstate==None:                   # handle a newstate of none, typically means the object didn't exist.
      newstate=self.get_state(target)    # if thats the case, just return the state of the target so nothing changes.
    try:
      currenttemp=int(float(newstate))
    except:
      a=0
    if newstate in ["home","house","Home","House"]:  # deal with having multiple versions of house and home to account for.
      newstate="home"
    elif newstate == "unk":
      newstate=self.get_state(target)
    return newstate

  def check_overide_active(self,target):
    override_active=False
    for override in self.targets[target]["overrides"]:
      if self.get_state(override)=="on":
        return True

