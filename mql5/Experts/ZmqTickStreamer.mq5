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
input string   ZMQ_REP_ADDRESS   = "tcp://*:5557";     // ZeroMQ reply address for confirmations
input bool     ENABLE_TICK_DATA  = true;               // Enable tick data streaming
input bool     ENABLE_BAR_DATA   = false;              // Enable bar data streaming (on new bar)
input int      TICK_PUBLISH_RATE = 10;                 // Tick publishing rate (1 = every tick, 10 = every 10th tick)
input bool     ENABLE_CONFIRMATIONS = true;            // Enable reception confirmations
input int      CONFIRMATION_TIMEOUT_MS = 500;          // Timeout for confirmations in milliseconds

// Global variables
CZmqSocket     *g_publisher;      // PUB socket for tick streaming
CZmqSocket     *g_responder;      // REP socket for confirmations
int             g_tick_counter;
datetime        g_last_bar_time;
bool            g_awaiting_confirmation;
ulong           g_last_message_time;
long            g_symbols_seq_nums[100]; // Array to store sequence numbers for up to 100 symbols
string          g_symbol_list[100];      // Array to store symbol names
int             g_symbol_count;         // Number of tracked symbols

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize ZeroMQ PUB socket
    g_publisher = new CZmqSocket(ZMQ_PUB);
    if(!g_publisher.Create())
    {
        Print("Failed to create ZeroMQ PUB socket: ", g_publisher.GetLastError());
        return INIT_FAILED;
    }
    
    // Bind PUB socket to address
    if(!g_publisher.Bind(ZMQ_PUB_ADDRESS))
    {
        Print("Failed to bind ZeroMQ PUB socket to ", ZMQ_PUB_ADDRESS, ": ", g_publisher.GetLastError());
        return INIT_FAILED;
    }
    
    // Initialize ZeroMQ REP socket if confirmations enabled
    if(ENABLE_CONFIRMATIONS)
    {
        g_responder = new CZmqSocket(ZMQ_REP);
        if(!g_responder.Create())
        {
            Print("Failed to create ZeroMQ REP socket: ", g_responder.GetLastError());
            return INIT_FAILED;
        }
        
        // Bind REP socket to address
        if(!g_responder.Bind(ZMQ_REP_ADDRESS))
        {
            Print("Failed to bind ZeroMQ REP socket to ", ZMQ_REP_ADDRESS, ": ", g_responder.GetLastError());
            return INIT_FAILED;
        }
    }
    
    Print("ZeroMQ tick streamer initialized on ", ZMQ_PUB_ADDRESS);
    if(ENABLE_CONFIRMATIONS)
        Print("Confirmation socket ready on ", ZMQ_REP_ADDRESS);
    Print("Tick data streaming: ", ENABLE_TICK_DATA ? "Enabled" : "Disabled");
    Print("Bar data streaming: ", ENABLE_BAR_DATA ? "Enabled" : "Disabled");
    
    // Initialize counters and arrays
    g_tick_counter = 0;
    g_last_bar_time = 0;
    g_awaiting_confirmation = false;
    g_last_message_time = GetTickCount();
    g_symbol_count = 0;
    ArrayInitialize(g_symbols_seq_nums, 0);
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Clean up ZeroMQ sockets
    if(g_publisher != NULL)
    {
        g_publisher.Close();
        delete g_publisher;
        g_publisher = NULL;
    }
    
    if(g_responder != NULL)
    {
        g_responder.Close();
        delete g_responder;
        g_responder = NULL;
    }
    
    Print("ZeroMQ tick streamer stopped");
}

//+------------------------------------------------------------------+
//| Find index of symbol in our tracking arrays or add if not found  |
//+------------------------------------------------------------------+
int FindOrAddSymbol(string symbol)
{
    // Check if symbol already exists in our list
    for(int i = 0; i < g_symbol_count; i++)
    {
        if(g_symbol_list[i] == symbol)
            return i;
    }
    
    // If we have room, add the new symbol
    if(g_symbol_count < 100)
    {
        g_symbol_list[g_symbol_count] = symbol;
        g_symbols_seq_nums[g_symbol_count] = 0; // Initialize sequence number
        return g_symbol_count++;
    }
    
    // If we're out of space, reuse the first slot (not ideal but prevents overflow)
    Print("WARNING: Symbol tracking array full, reusing first slot for ", symbol);
    g_symbol_list[0] = symbol;
    g_symbols_seq_nums[0] = 0;
    return 0;
}

//+------------------------------------------------------------------+
//| Process confirmation requests if enabled                        |
//+------------------------------------------------------------------+
void ProcessConfirmations()
{
    if(!ENABLE_CONFIRMATIONS || g_responder == NULL)
        return;
        
    // Check for confirmation messages with non-blocking receive
    string confirmation = g_responder.Receive(true);
    if(confirmation != "")
    {
        // Send ACK response
        g_responder.Send("ACK");
        g_awaiting_confirmation = false;
        g_last_message_time = GetTickCount();
    }
    
    // Check if we've been waiting too long for confirmation
    if(g_awaiting_confirmation && (GetTickCount() - g_last_message_time > CONFIRMATION_TIMEOUT_MS))
    {
        Print("Warning: Confirmation timeout exceeded");
        g_awaiting_confirmation = false;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Process any pending confirmations
    ProcessConfirmations();
    
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
                // Find the symbol in our tracking arrays or add it
                int symbolIndex = FindOrAddSymbol(_Symbol);
                
                // Increment sequence number for this symbol
                g_symbols_seq_nums[symbolIndex]++;
                
                // Convert tick to JSON
                string tick_json = TickToJson(tick);
                
                // Inject sequence number into the JSON
                // Remove the closing brace, add sequence number, then close it again
                tick_json = StringSubstr(tick_json, 0, StringLen(tick_json) - 1) + 
                           ",\"seq_num\":" + IntegerToString(g_symbols_seq_nums[symbolIndex]) + "}";
                
                // Send tick data via ZeroMQ
                string topic = "TICK|" + _Symbol;
                string message = topic + "|" + tick_json;
                
                if(!g_publisher.Send(message))
                {
                    Print("Failed to send tick data: ", g_publisher.GetLastError());
                }
                else if(ENABLE_CONFIRMATIONS)
                {
                    g_awaiting_confirmation = true;
                    g_last_message_time = GetTickCount();
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
                // Find the symbol in our tracking arrays or add it
                int symbolIndex = FindOrAddSymbol(_Symbol);
                
                // Increment sequence number for this symbol
                g_symbols_seq_nums[symbolIndex]++;
                
                // Convert bar data to JSON
                string bar_json = BarToJson(_Symbol, PERIOD_CURRENT, 
                                           rates[0].time, rates[0].open, rates[0].high,
                                           rates[0].low, rates[0].close, rates[0].tick_volume);
                
                // Inject sequence number into the JSON
                bar_json = StringSubstr(bar_json, 0, StringLen(bar_json) - 1) + 
                          ",\"seq_num\":" + IntegerToString(g_symbols_seq_nums[symbolIndex]) + "}";
                
                // Send bar data via ZeroMQ
                string topic = "BAR|" + _Symbol + "|" + EnumToString(PERIOD_CURRENT);
                string message = topic + "|" + bar_json;
                
                if(!g_publisher.Send(message))
                {
                    Print("Failed to send bar data: ", g_publisher.GetLastError());
                }
                else if(ENABLE_CONFIRMATIONS)
                {
                    g_awaiting_confirmation = true;
                    g_last_message_time = GetTickCount();
                }
            }
            
            g_last_bar_time = current_bar_time;
        }
    }
} 