//+------------------------------------------------------------------+
//|                                                   ZmqHelper.mqh |
//|                        Copyright 2023, MetaQuotes Software Corp. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023, MetaQuotes Software Corp."
#property link      "https://www.mql5.com"
#property strict

#include <ZMQ/ZmqSocket.mqh>

//+------------------------------------------------------------------+
//| Convert tick to JSON string                                      |
//+------------------------------------------------------------------+
string TickToJson(MqlTick &tick)
{
   string json = "{";
   json += "\"symbol\":\"" + _Symbol + "\",";
   json += "\"time\":" + IntegerToString(tick.time) + ",";
   json += "\"bid\":" + DoubleToString(tick.bid, 8) + ",";
   json += "\"ask\":" + DoubleToString(tick.ask, 8) + ",";
   json += "\"last\":" + DoubleToString(tick.last, 8) + ",";
   json += "\"volume\":" + IntegerToString(tick.volume) + ",";
   json += "\"flags\":" + IntegerToString(tick.flags);
   json += "}";
   
   return json;
}

//+------------------------------------------------------------------+
//| Convert bar data to JSON string                                  |
//+------------------------------------------------------------------+
string BarToJson(string symbol, ENUM_TIMEFRAMES timeframe, 
                 datetime time, double open, double high, 
                 double low, double close, long volume)
{
   string tf = "";
   
   switch(timeframe)
   {
      case PERIOD_M1:  tf = "M1";  break;
      case PERIOD_M5:  tf = "M5";  break;
      case PERIOD_M15: tf = "M15"; break;
      case PERIOD_M30: tf = "M30"; break;
      case PERIOD_H1:  tf = "H1";  break;
      case PERIOD_H4:  tf = "H4";  break;
      case PERIOD_D1:  tf = "D1";  break;
      case PERIOD_W1:  tf = "W1";  break;
      case PERIOD_MN1: tf = "MN1"; break;
      default:         tf = "M1";  break;
   }
   
   string json = "{";
   json += "\"symbol\":\"" + symbol + "\",";
   json += "\"timeframe\":\"" + tf + "\",";
   json += "\"time\":" + IntegerToString(time) + ",";
   json += "\"open\":" + DoubleToString(open, 8) + ",";
   json += "\"high\":" + DoubleToString(high, 8) + ",";
   json += "\"low\":" + DoubleToString(low, 8) + ",";
   json += "\"close\":" + DoubleToString(close, 8) + ",";
   json += "\"volume\":" + IntegerToString(volume);
   json += "}";
   
   return json;
}

//+------------------------------------------------------------------+
//| Get current timestamp in milliseconds                           |
//+------------------------------------------------------------------+
long GetTimestampMS()
{
   return TimeCurrent() * 1000;
} 