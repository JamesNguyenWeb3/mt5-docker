//+------------------------------------------------------------------+
//|                                                   ZmqSocket.mqh |
//|                        Copyright 2023, MetaQuotes Software Corp. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023, MetaQuotes Software Corp."
#property link      "https://www.mql5.com"
#property strict

// ZeroMQ Version
#define ZMQ_VERSION_MAJOR 4
#define ZMQ_VERSION_MINOR 3
#define ZMQ_VERSION_PATCH 2

// Socket types
#define ZMQ_PAIR 0
#define ZMQ_PUB 1
#define ZMQ_SUB 2
#define ZMQ_REQ 3
#define ZMQ_REP 4
#define ZMQ_DEALER 5
#define ZMQ_ROUTER 6
#define ZMQ_PULL 7
#define ZMQ_PUSH 8
#define ZMQ_XPUB 9
#define ZMQ_XSUB 10
#define ZMQ_STREAM 11

// Socket options
#define ZMQ_AFFINITY 4
#define ZMQ_IDENTITY 5
#define ZMQ_SUBSCRIBE 6
#define ZMQ_UNSUBSCRIBE 7
#define ZMQ_RATE 8
#define ZMQ_RECOVERY_IVL 9
#define ZMQ_SNDBUF 11
#define ZMQ_RCVBUF 12
#define ZMQ_RCVMORE 13
#define ZMQ_FD 14
#define ZMQ_EVENTS 15
#define ZMQ_TYPE 16
#define ZMQ_LINGER 17
#define ZMQ_RECONNECT_IVL 18
#define ZMQ_BACKLOG 19
#define ZMQ_RECONNECT_IVL_MAX 21
#define ZMQ_MAXMSGSIZE 22
#define ZMQ_SNDHWM 23
#define ZMQ_RCVHWM 24
#define ZMQ_MULTICAST_HOPS 25
#define ZMQ_RCVTIMEO 27
#define ZMQ_SNDTIMEO 28
#define ZMQ_LAST_ENDPOINT 32
#define ZMQ_ROUTER_MANDATORY 33
#define ZMQ_TCP_KEEPALIVE 34
#define ZMQ_TCP_KEEPALIVE_CNT 35
#define ZMQ_TCP_KEEPALIVE_IDLE 36
#define ZMQ_TCP_KEEPALIVE_INTVL 37
#define ZMQ_IMMEDIATE 39
#define ZMQ_XPUB_VERBOSE 40
#define ZMQ_ROUTER_RAW 41
#define ZMQ_IPV6 42
#define ZMQ_MECHANISM 43
#define ZMQ_PLAIN_SERVER 44
#define ZMQ_PLAIN_USERNAME 45
#define ZMQ_PLAIN_PASSWORD 46
#define ZMQ_CURVE_SERVER 47
#define ZMQ_CURVE_PUBLICKEY 48
#define ZMQ_CURVE_SECRETKEY 49
#define ZMQ_CURVE_SERVERKEY 50
#define ZMQ_PROBE_ROUTER 51
#define ZMQ_REQ_CORRELATE 52
#define ZMQ_REQ_RELAXED 53
#define ZMQ_CONFLATE 54
#define ZMQ_ZAP_DOMAIN 55
#define ZMQ_ROUTER_HANDOVER 56
#define ZMQ_TOS 57
#define ZMQ_CONNECT_RID 61
#define ZMQ_GSSAPI_SERVER 62
#define ZMQ_GSSAPI_PRINCIPAL 63
#define ZMQ_GSSAPI_SERVICE_PRINCIPAL 64
#define ZMQ_GSSAPI_PLAINTEXT 65
#define ZMQ_HANDSHAKE_IVL 66
#define ZMQ_SOCKS_PROXY 68
#define ZMQ_XPUB_NODROP 69
#define ZMQ_BLOCKY 70
#define ZMQ_XPUB_MANUAL 71
#define ZMQ_XPUB_WELCOME_MSG 72
#define ZMQ_STREAM_NOTIFY 73
#define ZMQ_INVERT_MATCHING 74
#define ZMQ_HEARTBEAT_IVL 75
#define ZMQ_HEARTBEAT_TTL 76
#define ZMQ_HEARTBEAT_TIMEOUT 77
#define ZMQ_XPUB_VERBOSER 78
#define ZMQ_CONNECT_TIMEOUT 79
#define ZMQ_TCP_MAXRT 80
#define ZMQ_THREAD_SAFE 81
#define ZMQ_MULTICAST_MAXTPDU 84
#define ZMQ_VMCI_BUFFER_SIZE 85
#define ZMQ_VMCI_BUFFER_MIN_SIZE 86
#define ZMQ_VMCI_BUFFER_MAX_SIZE 87
#define ZMQ_VMCI_CONNECT_TIMEOUT 88
#define ZMQ_USE_FD 89

// Message options
#define ZMQ_MORE 1
#define ZMQ_SRCFD 2
#define ZMQ_SHARED 3

// Send/recv options
#define ZMQ_DONTWAIT 1
#define ZMQ_SNDMORE 2

// Import the ZeroMQ DLL functions
#import "libzmq.dll"
   // Context API
   void *zmq_ctx_new();
   int   zmq_ctx_term(void *context);
   
   // Socket API
   void *zmq_socket(void *context, int type);
   int   zmq_close(void *socket);
   int   zmq_bind(void *socket, const char *endpoint);
   int   zmq_connect(void *socket, const char *endpoint);
   int   zmq_setsockopt(void *socket, int option, const void *optval, size_t optvallen);
   
   // Message API
   int   zmq_send(void *socket, const void *buf, size_t len, int flags);
   int   zmq_recv(void *socket, void *buf, size_t len, int flags);
   
   // Error handling
   int   zmq_errno();
   const char *zmq_strerror(int errnum);
#import

//+------------------------------------------------------------------+
//| ZeroMQ Socket Wrapper Class                                      |
//+------------------------------------------------------------------+
class CZmqSocket
{
private:
   void              *m_context;
   void              *m_socket;
   int                m_socket_type;
   string             m_endpoint;
   bool               m_connected;
   
public:
                     CZmqSocket(int socket_type);
                    ~CZmqSocket();
   
   bool              Create();
   bool              Bind(string endpoint);
   bool              Connect(string endpoint);
   bool              Send(string message, bool nonblocking=false);
   string            Receive(bool nonblocking=false);
   void              Close();
   string            GetLastError();
};

//+------------------------------------------------------------------+
//| Constructor                                                      |
//+------------------------------------------------------------------+
CZmqSocket::CZmqSocket(int socket_type)
{
   m_context = NULL;
   m_socket = NULL;
   m_socket_type = socket_type;
   m_connected = false;
}

//+------------------------------------------------------------------+
//| Destructor                                                       |
//+------------------------------------------------------------------+
CZmqSocket::~CZmqSocket()
{
   Close();
}

//+------------------------------------------------------------------+
//| Create socket                                                    |
//+------------------------------------------------------------------+
bool CZmqSocket::Create()
{
   // Create context if it doesn't exist
   if(m_context == NULL)
      m_context = zmq_ctx_new();
   
   // Create socket
   m_socket = zmq_socket(m_context, m_socket_type);
   
   return m_socket != NULL;
}

//+------------------------------------------------------------------+
//| Bind socket to endpoint                                          |
//+------------------------------------------------------------------+
bool CZmqSocket::Bind(string endpoint)
{
   if(m_socket == NULL)
      if(!Create())
         return false;
   
   m_endpoint = endpoint;
   int result = zmq_bind(m_socket, endpoint);
   m_connected = (result == 0);
   
   return m_connected;
}

//+------------------------------------------------------------------+
//| Connect socket to endpoint                                       |
//+------------------------------------------------------------------+
bool CZmqSocket::Connect(string endpoint)
{
   if(m_socket == NULL)
      if(!Create())
         return false;
   
   m_endpoint = endpoint;
   int result = zmq_connect(m_socket, endpoint);
   m_connected = (result == 0);
   
   return m_connected;
}

//+------------------------------------------------------------------+
//| Send message                                                     |
//+------------------------------------------------------------------+
bool CZmqSocket::Send(string message, bool nonblocking=false)
{
   if(m_socket == NULL || !m_connected)
      return false;
   
   int flags = nonblocking ? ZMQ_DONTWAIT : 0;
   int result = zmq_send(m_socket, message, StringLen(message), flags);
   
   return result >= 0;
}

//+------------------------------------------------------------------+
//| Receive message                                                  |
//+------------------------------------------------------------------+
string CZmqSocket::Receive(bool nonblocking=false)
{
   if(m_socket == NULL || !m_connected)
      return "";
   
   char buffer[1024] = {0};
   int flags = nonblocking ? ZMQ_DONTWAIT : 0;
   int result = zmq_recv(m_socket, buffer, 1024, flags);
   
   if(result > 0)
      return CharArrayToString(buffer, 0, result);
   
   return "";
}

//+------------------------------------------------------------------+
//| Close socket and context                                         |
//+------------------------------------------------------------------+
void CZmqSocket::Close()
{
   if(m_socket != NULL)
   {
      zmq_close(m_socket);
      m_socket = NULL;
      m_connected = false;
   }
   
   if(m_context != NULL)
   {
      zmq_ctx_term(m_context);
      m_context = NULL;
   }
}

//+------------------------------------------------------------------+
//| Get last error                                                   |
//+------------------------------------------------------------------+
string CZmqSocket::GetLastError()
{
   int error_code = zmq_errno();
   return StringFormat("Error %d: %s", error_code, zmq_strerror(error_code));
} 