import React, { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Collapse,
  IconButton,
  Chip,
  Tooltip,
  Button,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import BuildIcon from '@mui/icons-material/Build';
import RefreshIcon from '@mui/icons-material/Refresh';
import LaunchIcon from '@mui/icons-material/Launch';
import LoopIcon from '@mui/icons-material/Loop';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { useNavigate } from 'react-router-dom';
import agentService from '../services/agentService';

// Chain View: tree-indented rendering of an agent's transitive gofannon_agents
// dependencies and MCP tool references.
//
// The backend (/agents/{id}/chain) returns a flat {nodes, edges, root} graph.
// We fold it back into a tree for rendering: each agent node's children are
// the edges originating from it. This loses information only in the
// shared-dependency case (agent A and B both call agent C), where C will
// appear under both parents — which is arguably correct for "show me the
// call structure from this root."
//
// Cycles are handled here: when we follow an edge marked cyclic, we render
// the child as a leaf with a loop badge and don't recurse further. The
// backend already marks these — we trust its judgment rather than tracking
// an ancestry set on the client.

const AgentNode = ({ node, childEdges, nodesMap, onNavigate, depth, isCyclicRef }) => {
  // Leaf expansion defaults: root always open, deeper nodes start collapsed so
  // a 12-agent chain doesn't eat the viewport.
  const [open, setOpen] = useState(depth === 0);
  const hasChildren = childEdges && childEdges.length > 0;

  return (
    <Box sx={{ mt: depth === 0 ? 0 : 0.5 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          p: 1,
          borderRadius: 1,
          bgcolor: depth === 0 ? 'action.hover' : 'transparent',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        {hasChildren ? (
          <IconButton
            size="small"
            onClick={() => setOpen((v) => !v)}
            sx={{ p: 0.25 }}
            aria-label={open ? 'Collapse' : 'Expand'}
          >
            {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
          </IconButton>
        ) : (
          <Box sx={{ width: 26 }} />
        )}

        <SmartToyIcon fontSize="small" sx={{ color: node.missing ? 'error.main' : 'primary.main' }} />

        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {node.name || '(unnamed)'}
            </Typography>
            {node.missing && (
              <Tooltip title="This agent was deleted but another agent still references it." arrow>
                <Chip
                  icon={<WarningAmberIcon sx={{ fontSize: '14px !important' }} />}
                  label="Missing"
                  size="small"
                  color="error"
                  sx={{ height: 20, fontSize: '0.7rem' }}
                />
              </Tooltip>
            )}
            {node.truncated && (
              <Tooltip title="Maximum chain depth reached. Further dependencies not shown." arrow>
                <Chip label="Truncated" size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
              </Tooltip>
            )}
            {isCyclicRef && (
              <Tooltip title="Cycle detected. This agent also calls an ancestor." arrow>
                <Chip
                  icon={<LoopIcon sx={{ fontSize: '14px !important' }} />}
                  label="Cycle"
                  size="small"
                  color="warning"
                  sx={{ height: 20, fontSize: '0.7rem' }}
                />
              </Tooltip>
            )}
          </Box>
          {node.description && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {node.description}
            </Typography>
          )}
        </Box>

        {!node.missing && (
          <Tooltip title="Open this agent" arrow>
            <IconButton
              size="small"
              onClick={() => onNavigate(node.id)}
              sx={{ p: 0.5 }}
            >
              <LaunchIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {hasChildren && (
        <Collapse in={open} timeout="auto" unmountOnExit>
          <Box sx={{ pl: 3, borderLeft: '1px dashed', borderColor: 'divider', ml: 1.5 }}>
            {childEdges.map((edge, idx) => {
              const childNode = nodesMap[edge.to];
              if (!childNode) return null;
              if (childNode.type === 'mcp_server') {
                return <McpNode key={`${edge.from}->${edge.to}-${idx}`} node={childNode} edge={edge} />;
              }
              const childOwnEdges = isCyclicRef
                ? [] // already a cycle; backend won't have recursed
                : (nodesMap.__edgesByFrom[edge.to] || []);
              return (
                <AgentNode
                  key={`${edge.from}->${edge.to}-${idx}`}
                  node={childNode}
                  childEdges={edge.cyclic ? [] : childOwnEdges}
                  nodesMap={nodesMap}
                  onNavigate={onNavigate}
                  depth={depth + 1}
                  isCyclicRef={Boolean(edge.cyclic)}
                />
              );
            })}
          </Box>
        </Collapse>
      )}
    </Box>
  );
};

AgentNode.propTypes = {
  node: PropTypes.object.isRequired,
  childEdges: PropTypes.array,
  nodesMap: PropTypes.object.isRequired,
  onNavigate: PropTypes.func.isRequired,
  depth: PropTypes.number.isRequired,
  isCyclicRef: PropTypes.bool,
};

const McpNode = ({ node, edge }) => (
  <Box
    sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 0.5,
      p: 1,
      mt: 0.5,
      borderRadius: 1,
      '&:hover': { bgcolor: 'action.hover' },
    }}
  >
    <Box sx={{ width: 26 }} />
    <BuildIcon fontSize="small" sx={{ color: 'success.main' }} />
    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          MCP
        </Typography>
        <Chip
          label={`${edge.tools?.length || node.tool_count || 0} tools`}
          size="small"
          sx={{ height: 20, fontSize: '0.7rem', bgcolor: 'success.light', color: 'success.contrastText' }}
        />
      </Box>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{
          display: 'block',
          fontFamily: 'monospace',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {node.url}
      </Typography>
      {edge.tools && edge.tools.length > 0 && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', mt: 0.25 }}
        >
          {edge.tools.join(', ')}
        </Typography>
      )}
    </Box>
  </Box>
);

McpNode.propTypes = {
  node: PropTypes.object.isRequired,
  edge: PropTypes.object.isRequired,
};

const AgentChainView = ({ agentId }) => {
  const navigate = useNavigate();
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await agentService.getChain(agentId);
      setGraph(data);
    } catch (err) {
      setError(err.message || 'Failed to load chain.');
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }
  if (error) {
    return (
      <Alert
        severity="error"
        action={
          <Button size="small" startIcon={<RefreshIcon />} onClick={load}>
            Retry
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }
  if (!graph || !graph.root || !graph.nodes) {
    return <Typography color="text.secondary">No chain data available.</Typography>;
  }

  // Build an {from: [edges...]} index so each AgentNode can look up its own
  // outgoing edges without a full scan. Stash it on nodesMap under a
  // reserved key so we don't need another prop.
  const edgesByFrom = {};
  (graph.edges || []).forEach((e) => {
    if (!edgesByFrom[e.from]) edgesByFrom[e.from] = [];
    edgesByFrom[e.from].push(e);
  });
  const nodesMap = { ...graph.nodes, __edgesByFrom: edgesByFrom };

  const rootNode = graph.nodes[graph.root];
  if (!rootNode) {
    return <Alert severity="warning">Chain root agent not found.</Alert>;
  }

  const rootEdges = edgesByFrom[graph.root] || [];
  const agentCount = Object.values(graph.nodes).filter((n) => n.type === 'agent').length;
  const mcpCount = Object.values(graph.nodes).filter((n) => n.type === 'mcp_server').length;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {agentCount} agent{agentCount === 1 ? '' : 's'}
          {mcpCount > 0 ? `, ${mcpCount} MCP server${mcpCount === 1 ? '' : 's'}` : ''} in this chain.
        </Typography>
        <Button size="small" startIcon={<RefreshIcon fontSize="small" />} onClick={load}>
          Refresh
        </Button>
      </Box>
      <AgentNode
        node={rootNode}
        childEdges={rootEdges}
        nodesMap={nodesMap}
        onNavigate={(id) => navigate(`/agent/${id}`)}
        depth={0}
        isCyclicRef={false}
      />
    </Box>
  );
};

AgentChainView.propTypes = {
  agentId: PropTypes.string.isRequired,
};

export default AgentChainView;
