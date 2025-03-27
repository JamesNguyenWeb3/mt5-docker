//+------------------------------------------------------------------+
//|                                            ZmqTickStreamer.mq5 |
//|                                              Copyright 2023,   |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023,"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

#include <ZMQ/ZmqSocket.mqh>
#include <ZMQ/ZmqHelper.mqh>

// Input parameters
input string   ZMQ_PUB_ADDRESS   = "tcp://*:5555";     // ZeroMQ publisher address
input bool     ENABLE_TICK_DATA  = true;               // Enable tick data streaming
input bool     ENABLE_BAR_DATA   = false;              // Enable bar data streaming (on new bar)
input int      TICK_PUBLISH_RATE = 10;                 // Tick publishing rate (1 = every tick, 10 = every 10th tick)

// Global variables
CZmqSocket     *g_publisher;
int             g_tick_counter;
datetime        g_last_bar_time;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize ZeroMQ socket
   g_publisher = new CZmqSocket(ZMQ_PUB);
   if(!g_publisher.Create())
   {
      Print("Failed to create ZeroMQ socket: ", g_publisher.GetLastError());
      return INIT_FAILED;
   }
   
   // Bind socket to address
   if(!g_publisher.Bind(ZMQ_PUB_ADDRESS))
   {
      Print("Failed to bind ZeroMQ socket to ", ZMQ_PUB_ADDRESS, ": ", g_publisher.GetLastError());
      return INIT_FAILED;
   }
   
   Print("ZeroMQ tick streamer initialized on ", ZMQ_PUB_ADDRESS);
   Print("Tick data streaming: ", ENABLE_TICK_DATA ? "Enabled" : "Disabled");
   Print("Bar data streaming: ", ENABLE_BAR_DATA ? "Enabled" : "Disabled");
   
   // Initialize counters
   g_tick_counter = 0;
   g_last_bar_time = 0;
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up ZeroMQ socket
   if(g_publisher != NULL)
   {
      g_publisher.Close();
      delete g_publisher;
      g_publisher = NULL;
   }
   
   Print("ZeroMQ tick streamer stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(ENABLE_TICK_DATA)
   {
      // Only publish every TICK_PUBLISH_RATE ticks
      g_tick_counter++;
      if(g_tick_counter >= TICK_PUBLISH_RATE)
      {
         g_tick_counter = 0;
         
         // Get current tick data
         MqlTick tick;
         if(SymbolInfoTick(_Symbol, tick))
         {
            // Convert tick to JSON
            string tick_json = TickToJson(tick);
            
            // Send tick data via ZeroMQ
            string topic = "TICK|" + _Symbol;
            string message = topic + "|" + tick_json;
            
            if(!g_publisher.Send(message))
            {
               Print("Failed to send tick data: ", g_publisher.GetLastError());
            }
         }
      }
   }
   
   if(ENABLE_BAR_DATA)
   {
      // Check if a new bar has formed
      datetime current_bar_time = iTime(_Symbol, PERIOD_CURRENT, 0);
      
      if(current_bar_time > g_last_bar_time)
      {
         // Get bar data
         MqlRates rates[1];
         if(CopyRates(_Symbol, PERIOD_CURRENT, 0, 1, rates) == 1)
         {
            // Convert bar data to JSON
            string bar_json = BarToJson(_Symbol, PERIOD_CURRENT, 
                                       rates[0].time, rates[0].open, rates[0].high,
                                       rates[0].low, rates[0].close, rates[0].tick_volume);
            
            // Send bar data via ZeroMQ
            string topic = "BAR|" + _Symbol + "|" + EnumToString(PERIOD_CURRENT);
            string message = topic + "|" + bar_json;
            
            if(!g_publisher.Send(message))
            {
               Print("Failed to send bar data: ", g_publisher.GetLastError());
            }
         }
         
         g_last_bar_time = current_bar_time;
      }
   }
} 