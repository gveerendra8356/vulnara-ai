// core/websocket_service.dart
//
// Wraps one WebSocket connection to `WSS /ws/scans/{scan_id}?token=...`
// (API contract section 7). One instance per open scan, per the
// contract's "one socket per scan" note -- created fresh each time a
// ScanStatusScreen is opened, closed when it's disposed.
//
// Responsibilities:
//   - Connect with the access token as a query param (contract requires
//     this -- WebSocket clients can't always set headers).
//   - Send the `{"event":"ping"}` heartbeat on an interval so
//     load-balancers/proxies don't kill an idle connection.
//   - Expose a broadcast Stream<WsEvent> of every server message
//     (`pong` included -- callers can just ignore it, no special-casing
//     needed here).
//   - On disconnect, expose that via the stream's onDone rather than
//     silently retrying -- the calling provider decides whether/when to
//     reconnect (e.g. only if the scan isn't already COMPLETED/FAILED).

import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/ws_event.dart';
import 'constants.dart';

class WebSocketService {
  WebSocketService({required this.scanId, required this.accessToken});

  final String scanId;
  final String accessToken;

  WebSocketChannel? _channel;
  Timer? _heartbeatTimer;
  final _controller = StreamController<WsEvent>.broadcast();

  Stream<WsEvent> get events => _controller.stream;

  void connect() {
    final uri = Uri.parse('${ApiConfig.wsBaseUrl}/ws/scans/$scanId?token=$accessToken');
    _channel = WebSocketChannel.connect(uri);

    _channel!.stream.listen(
      (raw) {
        try {
          final json = jsonDecode(raw as String) as Map<String, dynamic>;
          _controller.add(WsEvent.fromJson(json));
        } catch (_) {
          // Malformed frame -- drop it rather than crash the stream for
          // every other listener on this broadcast controller.
        }
      },
      onDone: () {
        _heartbeatTimer?.cancel();
        if (!_controller.isClosed) _controller.close();
      },
      onError: (Object _) {
        _heartbeatTimer?.cancel();
        if (!_controller.isClosed) _controller.close();
      },
    );

    // Contract: client -> server heartbeat is `{"event":"ping"}`,
    // server replies `{"event":"pong", ...}`. 25s keeps well under most
    // reverse-proxy idle-connection timeouts (commonly 60s).
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 25), (_) {
      _channel?.sink.add(jsonEncode({'event': 'ping'}));
    });
  }

  void dispose() {
    _heartbeatTimer?.cancel();
    _channel?.sink.close();
    if (!_controller.isClosed) _controller.close();
  }
}
