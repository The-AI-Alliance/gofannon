import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  CircularProgress,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CloudIcon from '@mui/icons-material/Cloud';
import EditIcon from '@mui/icons-material/Edit';
import StorageIcon from '@mui/icons-material/Storage';
import agentService from '../services/agentService';
import demoService from '../services/demoService';
import dataStoreService from '../services/dataStoreService';

const HomePage = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [demoApps, setDemoApps] = useState([]);
  const [dataStoreNamespaces, setDataStoreNamespaces] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [loadingDemos, setLoadingDemos] = useState(true);
  const [loadingDataStores, setLoadingDataStores] = useState(true);
  const [agentFilter, setAgentFilter] = useState('all');

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const data = await agentService.getAgents();
        const withDeployment = await Promise.all(
          data.map(async (agent) => {
            try {
              const deployment = await agentService.getDeployment(agent._id);
              return { ...agent, isDeployed: deployment?.is_deployed, deployedName: deployment?.friendly_name };
            } catch {
              return { ...agent, isDeployed: false };
            }
          })
        );
        setAgents(
          withDeployment.sort((a, b) =>
            (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' })
          )
        );
      } catch (err) {
        console.error('Failed to fetch agents:', err);
      } finally {
        setLoadingAgents(false);
      }
    };

    const fetchDemos = async () => {
      try {
        const data = await demoService.getDemos();
        setDemoApps(data);
      } catch (err) {
        console.error('Failed to fetch demos:', err);
      } finally {
        setLoadingDemos(false);
      }
    };

    const fetchDataStores = async () => {
      try {
        const resp = await dataStoreService.listNamespaces();
        setDataStoreNamespaces((resp?.namespaces) || []);
      } catch (err) {
        console.error('Failed to fetch data stores:', err);
      } finally {
        setLoadingDataStores(false);
      }
    };

    const fetchAll = () => {
      fetchAgents();
      fetchDemos();
      fetchDataStores();
    };

    fetchAll();

    // Refetch when the tab regains focus. Without this, namespaces
    // created in another tab/page (e.g., the agent sandbox) don't
    // appear here until a hard refresh — confusing the user about
    // what state actually exists.
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchAll();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  const filteredAgents = agentFilter === 'deployed' 
    ? agents.filter(a => a.isDeployed) 
    : agents;

  const deployedCount = agents.filter(a => a.isDeployed).length;

  return (
    <Box sx={{ p: 3, maxWidth: 1800, margin: '0 auto' }}>
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr', xl: '1fr 1fr 1fr' }, 
        gap: 3,
        alignItems: 'start'
      }}>
        
        {/* Agents Table */}
        <Paper sx={{ overflow: 'hidden' }}>
          <Box sx={{ 
            p: 2, 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            borderBottom: '1px solid #e4e4e7',
            bgcolor: '#fafafa'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>Agents</Typography>
              <ToggleButtonGroup
                value={agentFilter}
                exclusive
                onChange={(e, v) => v && setAgentFilter(v)}
                size="small"
                sx={{ 
                  '& .MuiToggleButton-root': { 
                    py: 0.25, 
                    px: 1.5, 
                    fontSize: '0.75rem',
                    textTransform: 'none',
                    borderColor: '#e4e4e7'
                  }
                }}
              >
                <ToggleButton value="all">All ({agents.length})</ToggleButton>
                <ToggleButton value="deployed">
                  <CloudIcon sx={{ fontSize: 14, mr: 0.5 }} />
                  Deployed ({deployedCount})
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>
            <Button 
              variant="contained" 
              size="small" 
              startIcon={<AddIcon />}
              onClick={() => navigate('/create-agent', { state: { fresh: true } })}
            >
              Create
            </Button>
          </Box>
          <TableContainer sx={{ maxHeight: 500 }}>
            {loadingAgents ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress size={28} />
              </Box>
            ) : filteredAgents.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  {agentFilter === 'deployed' ? 'No deployed agents' : 'No agents yet'}
                </Typography>
                {agentFilter === 'all' && (
                  <Button 
                    size="small" 
                    onClick={() => navigate('/create-agent', { state: { fresh: true } })}
                    sx={{ mt: 1 }}
                  >
                    Create your first agent
                  </Button>
                )}
              </Box>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredAgents.map((agent) => (
                    <TableRow 
                      key={agent._id} 
                      hover 
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/agent/${agent._id}`)}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {agent.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ 
                          display: 'block',
                          maxWidth: 250,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {agent.description || 'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {agent.isDeployed ? (
                          <Tooltip title={`/rest/${agent.deployedName}`} arrow>
                            <Chip 
                              icon={<CloudIcon sx={{ fontSize: '14px !important' }} />}
                              label="Deployed" 
                              size="small" 
                              sx={{ 
                                bgcolor: '#dcfce7', 
                                color: '#166534',
                                fontWeight: 500,
                                fontSize: '0.7rem',
                                height: 24,
                                '& .MuiChip-icon': { color: '#166534' }
                              }}
                            />
                          </Tooltip>
                        ) : (
                          <Chip 
                            label="Draft" 
                            size="small" 
                            sx={{ 
                              bgcolor: '#f4f4f5', 
                              color: '#71717a',
                              fontWeight: 500,
                              fontSize: '0.7rem',
                              height: 24
                            }}
                          />
                        )}
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Tooltip title="View" arrow>
                          <IconButton size="small" onClick={() => navigate(`/agent/${agent._id}`)}>
                            <VisibilityIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Sandbox" arrow>
                          <IconButton size="small" onClick={() => navigate(`/agent/${agent._id}/sandbox`)}>
                            <PlayArrowIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TableContainer>
        </Paper>

        {/* Demo Apps Table */}
        <Paper sx={{ overflow: 'hidden' }}>
          <Box sx={{ 
            p: 2, 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            borderBottom: '1px solid #e4e4e7',
            bgcolor: '#fafafa'
          }}>
            <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>Demo Apps</Typography>
            <Button 
              variant="contained" 
              size="small" 
              startIcon={<AddIcon />}
              onClick={() => navigate('/create-demo', { state: { fresh: true } })}
            >
              Create
            </Button>
          </Box>
          <TableContainer sx={{ maxHeight: 500 }}>
            {loadingDemos ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress size={28} />
              </Box>
            ) : demoApps.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">No demo apps yet</Typography>
                <Button 
                  size="small" 
                  onClick={() => navigate('/create-demo', { state: { fresh: true } })}
                  sx={{ mt: 1 }}
                >
                  Create your first demo
                </Button>
              </Box>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>APIs</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {demoApps.map((demo) => (
                    <TableRow 
                      key={demo._id} 
                      hover 
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/demos/${demo._id}`)}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {demo.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ 
                          display: 'block',
                          maxWidth: 250,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {demo.description || 'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={`${demo.selectedApis?.length || 0} APIs`}
                          size="small"
                          sx={{ 
                            bgcolor: '#f4f4f5', 
                            color: '#71717a',
                            fontWeight: 500,
                            fontSize: '0.7rem',
                            height: 24
                          }}
                        />
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Tooltip title="View" arrow>
                          <IconButton size="small" onClick={() => navigate(`/demos/${demo._id}`)}>
                            <VisibilityIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit" arrow>
                          <IconButton size="small" onClick={() => navigate(`/create-demo/canvas?edit=${demo._id}`)}>
                            <EditIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TableContainer>
        </Paper>

        {/* Data Stores Table */}
        <Paper sx={{ overflow: 'hidden' }}>
          <Box sx={{
            p: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid #e4e4e7',
            bgcolor: '#fafafa',
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <StorageIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>Data Stores</Typography>
              <Chip label={`All (${dataStoreNamespaces.length})`} size="small" sx={{ height: 22, fontSize: '0.72rem' }} />
            </Box>
            <Button
              variant="outlined"
              size="small"
              onClick={() => navigate('/data-stores')}
              disabled={dataStoreNamespaces.length === 0}
            >
              View all
            </Button>
          </Box>
          <TableContainer sx={{ maxHeight: 500 }}>
            {loadingDataStores ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress size={28} />
              </Box>
            ) : dataStoreNamespaces.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  No data stores yet
                </Typography>
                <Typography color="text.secondary" variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                  Namespaces appear here once an agent writes data.
                </Typography>
              </Box>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Namespace</TableCell>
                    <TableCell align="right">Records</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dataStoreNamespaces.slice(0, 5).map((ns) => (
                    <TableRow
                      key={ns.namespace}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/data-stores/${encodeURIComponent(ns.namespace)}`)}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>
                          {ns.namespace}
                        </Typography>
                        {(ns.agents || []).length > 0 && (
                          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                            {(ns.agents || []).slice(0, 2).map((a) => (
                              <Chip
                                key={a}
                                label={a}
                                size="small"
                                sx={{ height: 18, fontSize: '0.65rem', bgcolor: '#e0f2fe', color: '#075985' }}
                              />
                            ))}
                            {(ns.agents || []).length > 2 && (
                              <Chip
                                label={`+${ns.agents.length - 2}`}
                                size="small"
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            )}
                          </Box>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">
                          {(ns.recordCount || 0).toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Tooltip title="Browse" arrow>
                          <IconButton
                            size="small"
                            onClick={() => navigate(`/data-stores/${encodeURIComponent(ns.namespace)}`)}
                          >
                            <VisibilityIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TableContainer>
        </Paper>
      </Box>
    </Box>
  );
};

export default HomePage;