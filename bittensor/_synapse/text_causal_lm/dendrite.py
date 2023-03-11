# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import torch
import asyncio
import bittensor
from typing import Union, Optional

class TextCausalLMDendrite(torch.nn.Module):
    """ Dendrite for the connecting to text_causal_lm synapses"""

    def __init__(
            self,
            endpoint: Union[ 'bittensor.Endpoint', torch.Tensor ], 
            wallet: Optional[ 'bittensor.wallet' ]  = None,
            text_inputs_serializer_type: 'bittensor.serializer_type' = bittensor.proto.Serializer.MSGPACK,
            hidden_states_serializer_type: 'bittensor.serializer_type' = bittensor.proto.Serializer.MSGPACK,
        ):
        """ Initializes the Dendrite
            Args:
                endpoint (:obj:Union[]`bittensor.endpoint`, `required`):
                    bittensor endpoint object.
                wallet (:obj:`bittensor.wallet`, `optional`):
                    bittensor wallet object.
                text_inputs_serializer_type (:obj:`bittensor.proto.Serializer`, `optional`, defaults to bittensor.proto.Serializer.MSGPACK):
                    serializer type for text inputs.
                hidden_states_serializer_type (:obj:`bittensor.proto.Serializer`, `optional`, defaults to bittensor.proto.Serializer.MSGPACK):
                    serializer type for hidden states.
        """    
        super(TextCausalLMDendrite, self).__init__()
        if wallet is None: 
            wallet = bittensor.wallet()
        self.wallet = wallet
        if isinstance(endpoint, torch.Tensor ): 
            endpoint = bittensor.endpoint.from_tensor( endpoint )
        self.endpoint = endpoint
        self.receptor = bittensor.receptor( endpoint = self.endpoint, wallet = self.wallet )
        self._text_inputs_serializer_type = text_inputs_serializer_type
        self._hidden_states_serializer_type = hidden_states_serializer_type

    def forward( 
            self, 
            text_inputs: torch.FloatTensor, 
            timeout: float = bittensor.__blocktime__ 
        ) -> torch.FloatTensor:
        """ Forward call to the receptor.
            Args:
                text_inputs (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, sequence_length)`, `required`):
                    torch tensor of text inputs.
                timeout (:obj:`float`, `optional`, defaults to 5 seconds):
                    timeout for the forward call.
            Returns:
                hidden_states (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, sequence_length, hidden_size)`, `required`):
                    torch tensor of hidden states.
        """
        # Get the event loop.
        loop = asyncio.get_event_loop()
        # Run the async forward call.
        return loop.run_until_complete( 
            self.async_forward ( 
                text_inputs = text_inputs, 
                timeout = timeout
            ) )
    
    async def async_forward( 
            self, 
            text_inputs: 
            torch.FloatTensor, 
            timeout: float = bittensor.__blocktime__ 
        ) -> torch.FloatTensor:
        """ Forward call to the receptor.
            Args:
                text_inputs (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, sequence_length)`, `required`):
                    torch tensor of text inputs.
                timeout (:obj:`float`, `optional`, defaults to 5 seconds):
                    timeout for the forward call.
            Returns:
                hidden_states (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, sequence_length, hidden_size)`, `required`):
                    torch tensor of hidden states.
        """
        # Serialize the text inputs.
        text_serializer = bittensor.serializer( serializer_type = self._text_inputs_serializer_type )
        serialized_text = text_serializer.serialize( text_inputs, from_type = bittensor.proto.TensorType.TORCH )

        # Build the request.
        request = bittensor.ForwardTextCausalLMRequest(
            serialized_text_inputs = serialized_text,
            text_inputs_serializer_type = self._text_inputs_serializer_type,
            hidden_states_serializer_type = self._hidden_states_serializer_type,
        )

        # Make the forward call.
        asyncio_future = self.receptor.stub.ForwardTextLastHiddenState (
                request = request, 
                timeout = timeout,
                metadata = (
                    ('rpc-auth-header','Bittensor'),
                    ('bittensor-signature', self.receptor.sign() ),
                    ('bittensor-version',str(bittensor.__version_as_int__)),
                ))
        # Wait for the response.
        grpc_response = await asyncio.wait_for( asyncio_future, timeout = timeout )

        # Deserialize the hidden states.
        hidden_states_serializer = bittensor.serializer( serializer_type = self._hidden_states_serializer_type )
        hidden_states = hidden_states_serializer.deserialize( grpc_response.hidden_states, to_type = bittensor.proto.TensorType.TORCH )

        # Return the hidden states.
        return hidden_states

    